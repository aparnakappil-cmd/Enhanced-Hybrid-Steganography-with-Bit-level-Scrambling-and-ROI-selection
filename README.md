# Master Steganography Tool

A comprehensive Python-based steganography tool that allows you to hide secret text or images within various media formats, including Text, Images, Audio, and Video. The tool uses RC4 encryption to secure the hidden data and requires a secret key for both encryption and extraction.

## Features

This tool supports 5 different steganography techniques:

1. **Text in Text**: Hides an encrypted secret message inside a cover text file (`cover.txt`) using zero-width non-joiner characters.
2. **Text in Image**: Hides an encrypted secret message inside a cover image (`cover.jpg`) using Least Significant Bit (LSB) encoding, outputting a stego image (`stego_output.png`).
3. **Image in Image**: Hides an encrypted secret image (`secret_image.jpg`) inside a cover image (`cover.jpg`) using LSB encoding, extracting to `decrypted_secret.jpg`.
4. **Text in Audio**: Hides an encrypted secret message inside an audio file using LSB encoding, resulting in `cover_audio.wav`. If a cover audio doesn't exist, it generates a dummy sine wave audio file seamlessly.
5. **Text in Video**: Hides an encrypted secret message inside a video (`video.mp4`) using LSB encoding frame-by-frame, exporting to a lossless AVI format (`steg_v.avi`).

## Requirements

Ensure you have Python 3.x installed. You will need to install the required dependencies:

```bash
pip install -r requirements.txt
```

*(Note: The `opencv-python` and `numpy` libraries are required for image and video processing)*

## How to Use

1. **Configuration**:
   - The secret text message to be hidden is defined in `secret.txt`. Make sure to create or edit this file with your desired message.
   - For image-in-image steganography, place your secret image as `secret_image.jpg` and your cover image as `cover.jpg` in the same directory as the script.
   - For video steganography, ensure you have a short `video.mp4` file in the directory. A dummy video will be generated if it doesn't exist.

2. **Running the Tool**:
   Open a terminal in the project directory and run:

   ```bash
   python master_steganography.py
   ```

3. **Interacting with the Menu**:
   - The tool will present a numbered menu (1-6).
   - Enter the number corresponding to the steganography technique you wish to execute.
   - You will be prompted to enter the **Secret Key**. By default, the required key is `SUPERNOVA`.
   - The script will encode the data, save the output file, open the stego media preview for a few seconds, and then demonstrate successful extraction and decryption of the hidden message.

## Security

The tool uses RC4 stream cipher encryption for all payloads before embedding them into the cover media. This provides an additional layer of security beyond simply hiding the data.
