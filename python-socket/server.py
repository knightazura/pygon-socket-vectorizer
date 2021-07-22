import socket, io
from PIL import Image
import vectorizer # vectorizer: https://github.com/riandyrn/try-pytorch-vectorizer

HEADERSIZE = 10

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((socket.gethostname(), 1234))
s.listen(10)

print("Socket hostname is: ", socket.gethostname())

# Init. vectorizer
v = vectorizer.Vectorizer()

while True:
  client_socket, address = s.accept()
  print(f"New request from {address} has come!")

  # Flag if new request come
  msg_flag = False
  if address:
    msg_flag = True

  # Using bytearray rather than 'naive' concatenate is much faster
  # https://www.guyrutenberg.com/2020/04/04/fast-bytes-concatenation-in-python/
  full_msg = bytearray()
  
  new_msg = True 
  while msg_flag:
    msg = client_socket.recv(1024)

    if new_msg:
      msglen = int(msg[:HEADERSIZE])
      print("New message length: ", msglen)
      new_msg = False

    full_msg += msg

    # Check if it's end
    if len(full_msg) - HEADERSIZE == msglen:
      # Vectorize the image
      print("Message fully received. Start vectorizing the image!\n")
      vector = v.get_vector(Image.open(io.BytesIO(full_msg[HEADERSIZE:])))

      # Show / send the vector
      print(f"Vector:  {vector}")
      # client_socket.send(full_msg)

      # Reset the states
      new_msg = False
      msg_flag = False