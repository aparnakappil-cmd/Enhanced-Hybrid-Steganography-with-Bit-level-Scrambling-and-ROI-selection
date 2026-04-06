import cv2
import numpy as np
import os
import time
import subprocess
import wave
import struct
import math

def rc4_init(key):
    key = [ord(c) for c in key]
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    return S

def rc4_encrypt_decrypt(S, data_bytes):
    i = 0
    j = 0
    result = bytearray(len(data_bytes))
    for idx, b in enumerate(data_bytes):
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        k = S[(S[i] + S[j]) % 256]
        result[idx] = b ^ k
    return bytes(result)

def to_binary(data_bytes):
    return ''.join([format(b, '08b') for b in data_bytes])

def from_binary(binary_str):
    all_bytes = [binary_str[i: i+8] for i in range(0, len(binary_str), 8)]
    result = []
    for b in all_bytes:
        if len(b) < 8:
            break
        result.append(int(b, 2))
    return bytes(result)

def get_bits_from_bytes(data_bytes):
    return np.unpackbits(np.frombuffer(data_bytes, dtype=np.uint8))

def get_bytes_from_bits(bits_array):
    return np.packbits(bits_array).tobytes()

# ==========================================
# 1. TEXT IN TEXT STEGANOGRAPHY
# ==========================================
def text_in_text():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    secret_txt_path = os.path.join(base_dir, 'secret.txt')
    output_txt_path = os.path.join(base_dir, 'cover.txt')
    
    if not os.path.exists(secret_txt_path):
        print(f"Error: Could not find '{secret_txt_path}'.")
        return
        
    with open(secret_txt_path, 'r', encoding='utf-8') as f:
        secret_msg = f.read()
        
    print(f"Loaded secret message ({len(secret_msg)} chars).")
    
    # RC4 Encryption
    key = "MY_TXT_SECRET_KEY"
    S = rc4_init(key)
    encrypted_bytes = rc4_encrypt_decrypt(S, secret_msg.encode('utf-8'))
    
    # Prefix length (4 bytes)
    length_prefix = len(encrypted_bytes).to_bytes(4, byteorder='big')
    full_payload = length_prefix + encrypted_bytes
    
    # Binary conversion
    binary_payload = []
    for b in full_payload:
        binary_payload.extend(list(format(b, '08b')))
        
    zero_chars = []
    for bit in binary_payload:
        if bit == '1':
            zero_chars.append('\u200C') # Zero width non-joiner
        else:
            zero_chars.append('\u200B') # Zero width space
            
    hidden_string = "".join(zero_chars)
    
    dummy_text = "This is a cover text. Everything seems normal here. "
    stego_text = dummy_text + hidden_string
    
    print("Hiding text into cover.txt using zero-width characters...")
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write(stego_text)
        
    print(f"Secret text successfully hidden. Saved as '{output_txt_path}'.")
    
    try:
        os.startfile(output_txt_path)
    except Exception:
        pass
    
    time.sleep(1.0)
    print("\nExtracting hidden message from 'cover.txt'...")
    with open(output_txt_path, 'r', encoding='utf-8') as f:
        read_text = f.read()
        
    extracted_bits = []
    for char in read_text:
        if char == '\u200C':
            extracted_bits.append('1')
        elif char == '\u200B':
            extracted_bits.append('0')
            
    extracted_bin_str = "".join(extracted_bits)
    if len(extracted_bin_str) < 32:
        print("No hidden message found.")
        return
        
    extracted_bytes = bytearray()
    for i in range(0, len(extracted_bin_str), 8):
        byte_val = int(extracted_bin_str[i:i+8], 2)
        extracted_bytes.append(byte_val)
        
    if len(extracted_bytes) < 4:
        return
        
    length_bytes = extracted_bytes[:4]
    payload_length = int.from_bytes(length_bytes, byteorder='big')
    
    extracted_encrypted = extracted_bytes[4:4+payload_length]
    S2 = rc4_init(key)
    decrypted_bytes = rc4_encrypt_decrypt(S2, extracted_encrypted)
    decrypted_msg = decrypted_bytes.decode('utf-8', errors='ignore')
    
    print("\n-----------------------------")
    print("      DECRYPTED MESSAGE      ")
    print("-----------------------------")
    print(decrypted_msg)
    print("-----------------------------\n")


# ==========================================
# 2. TEXT IN IMAGE STEGANOGRAPHY
# ==========================================
def encode_lsb_image(image, binary_msg):
    flat_img = image.flatten()
    if len(binary_msg) > len(flat_img):
        raise ValueError("Message is too large to be encoded in the image.")
    for i in range(len(binary_msg)):
        flat_img[i] = (flat_img[i] & 254) | int(binary_msg[i])
    return flat_img.reshape(image.shape)

def decode_lsb_image(image, length_bits):
    flat_img = image.flatten()
    binary_msg = ""
    for i in range(length_bits):
        binary_msg += str(flat_img[i] & 1)
    return binary_msg

def text_in_image():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    secret_txt_path = os.path.join(base_dir, 'secret.txt')
    cover_jpg_path = os.path.join(base_dir, 'ece.jpg')
    output_path = os.path.join(base_dir, 'stego_output.png')

    if not os.path.exists(secret_txt_path):
        print(f"Error: Could not find '{secret_txt_path}'.")
        return
        
    with open(secret_txt_path, 'r', encoding='utf-8') as f:
        secret_msg = f.read()

    key = "MY_SECRET_KEY"
    S = rc4_init(key)
    encrypted_bytes = rc4_encrypt_decrypt(S, secret_msg.encode('utf-8'))
    
    length_prefix = len(encrypted_bytes).to_bytes(4, byteorder='big')
    full_payload_bytes = length_prefix + encrypted_bytes
    binary_payload = to_binary(full_payload_bytes)

    if not os.path.exists(cover_jpg_path):
        print(f"Error: Could not find cover image '{cover_jpg_path}'.")
        return
        
    image = cv2.imread(cover_jpg_path)
    if image is None:
        print(f"Error: Failed to load '{cover_jpg_path}'.")
        return

    print("Encoding message into image...")
    encoded_image = encode_lsb_image(image, binary_payload)

    cv2.imwrite(output_path, encoded_image)
    print(f"Message successfully hidden. Saved as '{output_path}'.")

    try:
        os.startfile(os.path.abspath(output_path))
    except Exception:
        pass
    
    time.sleep(1)
    print("\nExtracting hidden message for verification...")
    stego_img = cv2.imread(output_path)
    
    length_binary = decode_lsb_image(stego_img, 32)
    payload_length = int(length_binary, 2)
    
    total_bits = 32 + (payload_length * 8)
    full_extracted_binary = decode_lsb_image(stego_img, total_bits)
    
    extracted_payload_binary = full_extracted_binary[32:]
    extracted_encrypted_bytes = from_binary(extracted_payload_binary)
    
    S2 = rc4_init(key)
    decrypted_bytes = rc4_encrypt_decrypt(S2, extracted_encrypted_bytes)
    decrypted_msg = decrypted_bytes.decode('utf-8', errors='ignore')
    
    print("\n-----------------------------")
    print("      DECRYPTED MESSAGE      ")
    print("-----------------------------")
    print(decrypted_msg)
    print("-----------------------------\n")


# ==========================================
# 3. IMAGE IN IMAGE STEGANOGRAPHY
# ==========================================
def encode_lsb_img2img(image, binary_data):
    flat_img = image.flatten()
    bits = np.unpackbits(np.frombuffer(binary_data, dtype=np.uint8))
    
    if len(bits) > len(flat_img):
        raise ValueError(f"Payload too large. Need {len(bits)} bits, but capacity is {len(flat_img)} bits.")
        
    flat_img[:len(bits)] = (flat_img[:len(bits)] & 254) | bits
    return flat_img.reshape(image.shape)

def decode_lsb_img2img(image, byte_length):
    flat_img = image.flatten()
    total_bits = byte_length * 8
    extracted_bits = flat_img[:total_bits] & 1
    extracted_bytes = np.packbits(extracted_bits).tobytes()
    return extracted_bytes

def image_in_image():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    secret_path = os.path.join(base_dir, 'suguna.jpg')
    cover_jpg_path = os.path.join(base_dir, 'ece.jpg')
    output_path = os.path.join(base_dir, 'stego_image_output.png')

    if not os.path.exists(secret_path):
        print(f"Error: Could not find '{secret_path}'.")
        return
        
    with open(secret_path, 'rb') as f:
        secret_bytes = f.read()

    print(f"Secret image size: {len(secret_bytes)} bytes")
    key = "MY_SECRET_KEY"
    S = rc4_init(key)
    print("Encrypting secret image...")
    encrypted_bytes = rc4_encrypt_decrypt(S, secret_bytes)
    
    length_prefix = len(encrypted_bytes).to_bytes(4, byteorder='big')
    full_payload = length_prefix + encrypted_bytes
    
    print("Loading cover image...")
    image = cv2.imread(cover_jpg_path)
    if image is None:
        print(f"Error: Failed to load '{cover_jpg_path}'.")
        return
        
    max_bytes = (image.shape[0] * image.shape[1] * image.shape[2]) // 8
    
    if len(full_payload) > max_bytes:
        print("Resizing cover image to fit the payload...")
        required_pixels = len(full_payload) * 8 // 3 + 1
        scale = np.sqrt(required_pixels / (image.shape[0] * image.shape[1]))
        scale = max(scale, 1.0) * 1.05
        new_width = int(image.shape[1] * scale)
        new_height = int(image.shape[0] * scale)
        image = cv2.resize(image, (new_width, new_height))
    
    print("Encoding encrypted data into cover image...")
    encoded_image = encode_lsb_img2img(image, full_payload)
    cv2.imwrite(output_path, encoded_image)
    print(f"Secret image successfully hidden. Saved as '{output_path}'.")

    try:
        os.startfile(output_path)
    except Exception:
        pass
    
    time.sleep(1.0)
    print("\nExtracting hidden data from stego image...")
    stego_img = cv2.imread(output_path)
    length_bytes = decode_lsb_img2img(stego_img, 4)
    payload_length = int.from_bytes(length_bytes, byteorder='big')
    
    if payload_length <= 0 or payload_length > 50000000:
        print("Error: Extracted payload length is invalid.")
        return
        
    total_bytes = 4 + payload_length
    full_extracted_bytes = decode_lsb_img2img(stego_img, total_bytes)
    extracted_encrypted_bytes = full_extracted_bytes[4:]
    
    S2 = rc4_init(key)
    print("Decrypting extracted data...")
    decrypted_bytes = rc4_encrypt_decrypt(S2, extracted_encrypted_bytes)
    
    decrypted_output_path = os.path.join(base_dir, 'decrypted_secret.jpg')
    with open(decrypted_output_path, 'wb') as f:
        f.write(decrypted_bytes)
        
    print("\n-----------------------------")
    print(f"Saved decrypted image to '{decrypted_output_path}'")
    print("-----------------------------\n")

    try:
        os.startfile(decrypted_output_path)
    except Exception:
        pass


# ==========================================
# 4. TEXT IN AUDIO STEGANOGRAPHY
# ==========================================
def generate_dummy_audio(filepath):
    print(f"'{filepath}' not found. Generating a 5-second sine wave input audio...")
    with wave.open(filepath, 'w') as wave_file:
        wave_file.setnchannels(1)
        wave_file.setsampwidth(2)
        wave_file.setframerate(44100)
        sample_rate = 44100.0
        duration = 5
        values = []
        for i in range(int(duration * sample_rate)):
            values.append(int(10000.0 * math.sin(i / sample_rate * 2.0 * math.pi * 440.0)))
        wave_file.writeframes(struct.pack('h'*len(values), *values))

def encode_lsb_audio(audio_frames, binary_data):
    if len(binary_data) > len(audio_frames) // 2:
        raise ValueError("Payload too large for audio capacity.")
    for i in range(len(binary_data)):
        idx = i * 2 
        audio_frames[idx] = (audio_frames[idx] & 254) | int(binary_data[i])
    return audio_frames

def decode_lsb_audio(audio_frames, bit_length):
    extracted_bits = []
    for i in range(bit_length):
        idx = i * 2
        extracted_bits.append(str(audio_frames[idx] & 1))
    extracted_bin_str = "".join(extracted_bits)
    extracted_bytes = bytearray()
    for i in range(0, len(extracted_bin_str), 8):
        extracted_bytes.append(int(extracted_bin_str[i:i+8], 2))
    return bytes(extracted_bytes)

def text_in_audio():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    secret_txt_path = os.path.join(base_dir, 'secret.txt')
    input_audio_path = os.path.join(base_dir, 'input_audio.wav')
    output_audio_path = os.path.join(base_dir, 'cover_audio.wav') # AS REQUESTED

    if not os.path.exists(secret_txt_path):
        print(f"Error: Could not find '{secret_txt_path}'")
        return
        
    with open(secret_txt_path, 'r', encoding='utf-8') as f:
        secret_msg = f.read()

    if not os.path.exists(input_audio_path):
        generate_dummy_audio(input_audio_path)
        
    with wave.open(input_audio_path, 'r') as wave_read:
        params = wave_read.getparams()
        num_frames = wave_read.getnframes()
        frames = wave_read.readframes(num_frames)
        
    audio_frames = bytearray(frames)
    max_bytes = (len(audio_frames) // 2) // 8
    
    key = "MY_AUDIO_SECRET_KEY"
    S = rc4_init(key)
    encrypted_bytes = rc4_encrypt_decrypt(S, secret_msg.encode('utf-8'))
    
    length_prefix = len(encrypted_bytes).to_bytes(4, byteorder='big')
    full_payload = length_prefix + encrypted_bytes
    
    binary_payload = []
    for b in full_payload:
        binary_payload.extend(list(format(b, '08b')))
        
    if len(binary_payload) > len(audio_frames) // 2:
        print("Error: Message is too large to fit in this audio file.")
        return
        
    print("Encoding payload into audio frames...")
    encoded_frames = encode_lsb_audio(audio_frames, binary_payload)
    
    with wave.open(output_audio_path, 'w') as wave_write:
        wave_write.setparams(params)
        wave_write.writeframes(bytes(encoded_frames))
        
    print(f"Successfully hidden the message! Saved as '{output_audio_path}'")
    try:
        print("Opening audio player...")
        if os.name == 'nt':
            os.system(f'start "" "{output_audio_path}"')
        else:
            subprocess.run(["xdg-open", output_audio_path])
    except Exception as e:
        print(f"Could not play audio: {e}")
        pass
    
    print("Waiting 5 seconds for preview...")
    time.sleep(5.0)
    print("\nExtracting hidden message from audio...")
    with wave.open(output_audio_path, 'r') as wave_read2:
        num_frames2 = wave_read2.getnframes()
        stego_frames = bytearray(wave_read2.readframes(num_frames2))
        
    length_bytes = decode_lsb_audio(stego_frames, 32)
    payload_length = int.from_bytes(length_bytes, byteorder='big')
    
    if payload_length <= 0 or payload_length > max_bytes:
        print("Error: Invalid payload length extracted.")
        return
        
    total_bits = 32 + (payload_length * 8)
    full_extracted_bytes = decode_lsb_audio(stego_frames, total_bits)
    encrypted_extracted = full_extracted_bytes[4:]
    
    S2 = rc4_init(key)
    decrypted_bytes = rc4_encrypt_decrypt(S2, encrypted_extracted)
    decrypted_msg = decrypted_bytes.decode('utf-8', errors='ignore')
    
    print("\n-----------------------------")
    print("      DECRYPTED MESSAGE      ")
    print("-----------------------------")
    print(decrypted_msg)
    print("-----------------------------\n")


# ==========================================
# 5. TEXT IN VIDEO STEGANOGRAPHY
# ==========================================
def generate_dummy_video(filepath):
    print(f"'{filepath}' not found. Generating a 3-second dummy video...")
    width, height = 640, 480
    fps = 30
    duration = 3
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
    for i in range(fps * duration):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        x = (i * 10) % width
        y = (i * 5) % height
        cv2.rectangle(frame, (x, y), (x + 50, y + 50), (0, 255, 0), -1)
        out.write(frame)
    out.release()
    print("Dummy video generated.")

def preview_video(video_path, max_seconds=2):
    print(f"\nPreviewing original video '{os.path.basename(video_path)}' for {max_seconds} seconds...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    delay = int(1000 / fps)
    start_time = time.time()
    while True:
        ret, frame = cap.read()
        if not ret: break
        cv2.imshow('Original Video Preview', frame)
        if time.time() - start_time > max_seconds: break
        if cv2.waitKey(delay) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()

def encode_video(input_path, output_path, binary_payload):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened(): return False
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*'FFV1') # Lossless codec
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_bits = len(binary_payload)
    bit_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        if bit_idx < total_bits:
            flat_frame = frame.flatten()
            capacity = len(flat_frame)
            bits_to_embed = min(capacity, total_bits - bit_idx)
            flat_frame[:bits_to_embed] = (flat_frame[:bits_to_embed] & 254) | binary_payload[bit_idx : bit_idx + bits_to_embed]
            bit_idx += bits_to_embed
            frame = flat_frame.reshape(frame.shape)
        out.write(frame)
    cap.release()
    out.release()
    return bit_idx >= total_bits

def decode_video(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return None
    ret, first_frame = cap.read()
    if not ret: return None
    
    flat_first = first_frame.flatten()
    length_bits = flat_first[:32] & 1
    length_bytes = get_bytes_from_bits(length_bits)
    payload_length = int.from_bytes(length_bytes, byteorder='big')
    
    if payload_length <= 0 or payload_length > 10 * 1024 * 1024:
        cap.release()
        return None
        
    total_bits_needed = 32 + (payload_length * 8)
    extracted_bits = np.zeros(total_bits_needed, dtype=np.uint8)
    
    # Process the first frame which is already loaded
    capacity = len(flat_first)
    bits_to_extract = min(capacity, total_bits_needed)
    extracted_bits[:bits_to_extract] = flat_first[:bits_to_extract] & 1
    bit_idx = bits_to_extract
    
    # Read remaining frames only if the payload spans over multiple frames
    while bit_idx < total_bits_needed:
        ret, frame = cap.read()
        if not ret: break
        flat_frame = frame.flatten()
        capacity = len(flat_frame)
        bits_to_extract = min(capacity, total_bits_needed - bit_idx)
        extracted_bits[bit_idx : bit_idx + bits_to_extract] = flat_frame[:bits_to_extract] & 1
        bit_idx += bits_to_extract
        
    cap.release()
    
    full_extracted_bytes = get_bytes_from_bits(extracted_bits)
    return full_extracted_bytes[4:]

def text_in_video():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    secret_txt_path = os.path.join(base_dir, 'secret.txt')
    cover_video_path = os.path.join(base_dir, 'video.mp4')
    output_video_path = os.path.join(base_dir, 'steg_v.avi')

    if not os.path.exists(secret_txt_path):
        print(f"Error: Could not find '{secret_txt_path}'")
        return
        
    with open(secret_txt_path, 'r', encoding='utf-8') as f:
        secret_msg = f.read()

    if not os.path.exists(cover_video_path):
        generate_dummy_video(cover_video_path)

    key = "MY_VIDEO_SECRET_KEY"
    S = rc4_init(key)
    encrypted_bytes = rc4_encrypt_decrypt(S, secret_msg.encode('utf-8'))
    
    length_prefix = len(encrypted_bytes).to_bytes(4, byteorder='big')
    full_payload = length_prefix + encrypted_bytes
    binary_payload_bits = get_bits_from_bytes(full_payload)
    
    print("Encoding video...")
    success = encode_video(cover_video_path, output_video_path, binary_payload_bits)
    if not success:
         return
         
    print(f"Message successfully hidden! Saved as '{output_video_path}'.")
    try:
        print("Opening video player...")
        if os.name == 'nt':
            os.system(f'start "" "{output_video_path}"')
        else:
            subprocess.run(["xdg-open", output_video_path])
    except Exception as e:
        print(f"Could not play video: {e}")
        pass
    
    print("Wait 5 seconds for preview...")
    time.sleep(5.0)
    print("\nExtracting hidden message from stego video...")
    extracted_encrypted_bytes = decode_video(output_video_path)
    
    if extracted_encrypted_bytes is None:
        print("Error: Could not decode video.")
        return
        
    S2 = rc4_init(key)
    decrypted_bytes = rc4_encrypt_decrypt(S2, extracted_encrypted_bytes)
    decrypted_msg = decrypted_bytes.decode('utf-8', errors='ignore')
    
    print("\n-----------------------------")
    print("      DECRYPTED MESSAGE      ")
    print("-----------------------------")
    print(decrypted_msg)
    print("-----------------------------\n")


# ==========================================
# MAIN ROUTINE
# ==========================================
def main():
    while True:
        print("\n==================================")
        print("    MASTER STEGANOGRAPHY TOOL     ")
        print("==================================")
        print("1. Text in Text (Outputs cover.txt)")
        print("2. Text in Image (Outputs stego_output.png)")
        print("3. Image in Image (Outputs stego_image_output.png)")
        print("4. Text in Audio (Outputs cover_audio.wav)")
        print("5. Text in Video (Outputs steg_v.avi)")
        print("6. Exit")
        print("==================================")
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice in ['1', '2', '3', '4', '5']:
            secret_key = input("Enter secret key: ").strip()
            if secret_key != "SUPERNOVA":
                print("Invalid secret key. Access denied.")
                continue
                
            if choice == '1':
                text_in_text()
            elif choice == '2':
                text_in_image()
            elif choice == '3':
                image_in_image()
            elif choice == '4':
                text_in_audio()
            elif choice == '5':
                text_in_video()
        elif choice == '6':
            print("Exiting tool...")
            break
        else:
            print("Invalid choice. Please choose 1-6.")

if __name__ == '__main__':
    main()
