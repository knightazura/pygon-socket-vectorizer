import enum
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
import numpy as np
from PIL import Image

import warnings
# this is to supress bug warning from current version of pytorch
# check here for details: https://github.com/pytorch/pytorch/issues/54846
warnings.filterwarnings("ignore")


class VectorModels(enum.Enum):
    ResNet18 = 1
    MobileNetV2 = 2
    MobileNetV3 = 3

class Vectorizer:
    output_sizes = {
        VectorModels.ResNet18: 512,
        VectorModels.MobileNetV2: 1280,
        VectorModels.MobileNetV3: 1024
    }

    def __init__(self, cuda=False, model_name=VectorModels.ResNet18):
        # initialize image preprocessor for converting image binary
        # to format that match the input for vectorizer model
        self.image_preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])
        # determine model that we will be using for the vectorizer
        model = None
        extraction_layer = None
        if model_name is VectorModels.ResNet18:
            model = models.resnet18(pretrained=True)
            # in resnet18, the last layer before classification layer
            # is avgpool, so we will use output value in that layer
            extraction_layer = model.avgpool
        elif model_name is VectorModels.MobileNetV2:
            model = models.mobilenet_v2(pretrained=True)
            # in mobilenetv2, the last layer before classification layer
            # is located in classifier layers group, so we fetch it from
            # this group
            extraction_layer = model.classifier[-2]
        elif model_name is VectorModels.MobileNetV3:
            model = models.mobilenet_v3_small(pretrained=True)
            # in mobilenetv3, the last layer before classification layer
            # is located in classifier layers group, so we fetch it from
            # this group
            extraction_layer = model.classifier[-2]
        # set the model mode into evaluation mode, this mode is used
        # when the model is used for inferencing
        model.eval()
        # if cuda parameter is enabled but cuda is not available
        # raise exception
        if cuda and not torch.cuda.is_available():
            raise ValueError("Cuda is not available")
        # save cuda flag
        self.cuda = cuda
        if self.cuda:
            model.to('cuda')
        # set the model to property
        self.model = model
        self.model_name = model_name
        self.extraction_layer = extraction_layer

    def get_vector(self, img, tensor=False):
        # convert image binary into input tensor
        input_batch = self.image_preprocess(img).unsqueeze(0)
        if self.cuda:
            input_batch = input_batch.to('cuda')

        if self.model_name == VectorModels.ResNet18:
            output = torch.zeros(1, self.output_sizes[self.model_name], 1, 1)
        else:
            output = torch.zeros(1, self.output_sizes[self.model_name])

        def copy_data(m, i, o):
            output.copy_(o.data)

        h = self.extraction_layer.register_forward_hook(copy_data)
        self.model(input_batch)
        h.remove()

        if tensor:
            return output
        return output.flatten().numpy()