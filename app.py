from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import io
import numpy as np
import heapq
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# Exam presets
EXAM_SPECS = {
    'upsc': {'width': 200, 'height': 250, 'max_size': 50},
    'ssc': {'width': 150, 'height': 180, 'max_size': 30},
    'bank': {'width': 175, 'height': 220, 'max_size': 40},
    'nptel': {'width': 100, 'height': 120, 'max_size': 20},
    'gate': {'width': 180, 'height': 220, 'max_size': 40}
}

# ----------- Huffman Compression -----------

class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq

def build_huffman_tree(freq_dict):
    heap = [HuffmanNode(char, freq) for char, freq in freq_dict.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = HuffmanNode(None, left.freq + right.freq)
        merged.left = left
        merged.right = right
        heapq.heappush(heap, merged)
    return heap[0]

def build_huffman_codes(node, code='', codes=None):
    if codes is None:
        codes = {}
    if node is None:
        return
    if node.char is not None:
        codes[node.char] = code
    build_huffman_codes(node.left, code + '0', codes)
    build_huffman_codes(node.right, code + '1', codes)
    return codes

def huffman_compress(image_data):
    if isinstance(image_data, np.ndarray):
        image_data = image_data.tobytes()
    freq = defaultdict(int)
    for byte in image_data:
        freq[byte] += 1
    root = build_huffman_tree(freq)
    codes = build_huffman_codes(root)
    encoded = ''.join([codes[byte] for byte in image_data])
    padding = 8 - len(encoded) % 8
    encoded += '0' * padding
    byte_array = bytearray()
    for i in range(0, len(encoded), 8):
        byte_array.append(int(encoded[i:i + 8], 2))
    return bytes(byte_array)

# ----------- LZW Compression -----------

def lzw_compress(image_data):
    if isinstance(image_data, np.ndarray):
        image_data = image_data.tobytes()
    dict_size = 256
    dictionary = {bytes([i]): i for i in range(dict_size)}
    w = bytes()
    result = []
    for byte in image_data:
        wc = w + bytes([byte])
        if wc in dictionary:
            w = wc
        else:
            result.append(dictionary[w])
            dictionary[wc] = dict_size
            dict_size += 1
            w = bytes([byte])
    if w:
        result.append(dictionary[w])
    # Pack result into bytes
    compressed_bytes = bytearray()
    for code in result:
        compressed_bytes += code.to_bytes(2, 'big')  # 2-byte codes
    return bytes(compressed_bytes)

# ----------- Flask Route -----------

@app.route('/process_image', methods=['POST'])
def process_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400

        image_file = request.files['image']
        exam_type = request.form.get('exam_type')
        algorithm = request.form.get('algorithm')

        # Handle custom dimensions
        if exam_type == 'custom':
            try:
                width = int(request.form.get('custom_width'))
                height = int(request.form.get('custom_height'))
                max_size = int(request.form.get('custom_max_size'))
                spec = {'width': width, 'height': height, 'max_size': max_size}
            except:
                return jsonify({'error': 'Invalid custom dimension values'}), 400
        elif exam_type in EXAM_SPECS:
            spec = EXAM_SPECS[exam_type]
        else:
            return jsonify({'error': 'Invalid exam type'}), 400

        # Open and resize
        img = Image.open(image_file)
        img = img.resize((spec['width'], spec['height']))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img_array = np.array(img)

        # Apply compression algorithm
        if algorithm == 'huffman':
            compressed_data = huffman_compress(img_array)
        elif algorithm == 'lzw':
            compressed_data = lzw_compress(img_array)
        else:
            return jsonify({'error': 'Invalid compression algorithm'}), 400

        # Use compression size to adjust JPEG quality dynamically
        quality = 85
        if len(compressed_data) < 15000:
            quality = 70
        elif len(compressed_data) < 10000:
            quality = 50

        # Save final image
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality)
        output.seek(0)

        return send_file(
            output,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f'exam_photo_{exam_type}.jpg'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----------- Run App -----------

if __name__ == '__main__':
    app.run(debug=True)
