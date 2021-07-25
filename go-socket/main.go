package main

import (
	"bytes"
	"fmt"
	"image"
	"image/jpeg"
	"image/png"
	"io"
	"io/fs"
	"log"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
)

// All of these contsant values MUST BE SAME with socket app in python
const (
	BUFFERSIZE = 1024
	HEADERSIZE = 10
	PORT       = 1234
)

func main() {
	var wg sync.WaitGroup

	// Get local hostname
	hostname, err := os.Hostname()
	if err != nil {
		panic(err)
	}

	// Our images
	dir, err := os.ReadDir("./images")
	if err != nil {
		panic(err)
	}

	// Hit vectorizer concurrently!
	for _, d := range dir {
		wg.Add(1)
		vector := []float32{}

		// Connect to python vectorizer via socket
		conn, err := net.Dial("tcp", hostname+":"+strconv.Itoa(PORT))
		if err != nil {
			panic(err)
		}
		defer conn.Close()
		log.Println("Connected to server! Yay")

		go func(d fs.DirEntry) {
			// Read the image
			imgPath := "./images/" + d.Name()
			file, err := os.Open(imgPath)
			if err != nil {
				log.Fatalf("Error load image: %v", err)
			}
			// Get image type
			imgType := filepath.Ext(imgPath)

			// JPEG and PNG need different decoder!
			var img image.Image
			if imgType == ".png" {
				img, err = png.Decode(file)
			} else {
				img, _, err = image.Decode(file)
			}

			if err != nil {
				log.Fatalf("Fail decode image: %v", err)
			}

			// Encode image to binary (bytes?)
			imgBuf := new(bytes.Buffer)
			err = jpeg.Encode(imgBuf, img, nil)
			if err != nil {
				log.Fatalf("Fail encode image: %v", err)
			}

			// Add header for information of total length of the sent data
			header := fmt.Sprintf("%-10v", len(imgBuf.Bytes()))
			header += imgBuf.String()
			p := []byte(header)

			// Let's SEND!
			log.Println("Let's send the image!")
			conn.Write(p)

			log.Println("Image has been sent! Yay")
			defer wg.Done()
		}(d)

		// Receive the vector
		localBuffer := new(bytes.Buffer)
		readBuf := make([]byte, BUFFERSIZE)

		data := ""
		payloadSize := 0
		firstPacket := true
		for {
			dataLen, err := conn.Read(readBuf)
			if err != nil {
				if err == io.EOF {
					fmt.Println("Connection closed by client!")
					break
				}
			}

			localBuffer.Write(readBuf[:dataLen])

			// Read header on first packet to know total length/size of payload
			if firstPacket {

				// fmt.Println("FIRST PACKET")

				// Get the payload size from first 10 chars on the header
				payloadSize, _ = strconv.Atoi(strings.TrimSpace(string(localBuffer.Bytes()[:HEADERSIZE])))

				// First packet has been read, set the flag!
				firstPacket = false

				// Don't forget append first chunk of payload
				data += string(localBuffer.Bytes()[HEADERSIZE:])

			} else {

				// fmt.Println("OTHER PACKET")

				// Append payload chunks
				data += string(localBuffer.Bytes())

				// Check if current chunk is last part of payload
				if len(data) == payloadSize {
					// Parse data to proper format
					sv := strings.Split(data, " ")
					for _, v := range sv {
						fv, _ := strconv.ParseFloat(v, 64)
						vector = append(vector, float32(fv))
					}

					// Stop when finish read the payload
					break
				}
			}
			// fmt.Println("TOTAL LENGTH OF DATA: ", len(data))

			// Go to next chunk
			localBuffer.Next(BUFFERSIZE)
		}

		fmt.Println(len(vector))
	}
	wg.Wait()

}
