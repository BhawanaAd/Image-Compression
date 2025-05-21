from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import io
import numpy as np
import heapq
from collections import defaultdict

app = Flask(__name__)
CORS(app)

EXAM_SPECS = {
    'upsc': {'width': 110, 'height': 140, 'max_size': 290},
    'ssc': {'width': 100, 'height': 120, 'max_size': 45},
    'bank': {'width': 200, 'height': 230, 'max_size': 45},
    'nptel': {'width': 150, 'height': 200, 'max_size': 90},
    'gate': {'width': 240, 'height': 320, 'max_size': 195}
}

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

@app.route('/process_image', methods=['POST'])
def process_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400

        image_file = request.files['image']
        exam_type = request.form.get('exam_type')

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

        # Try to match the compressed size to max_size (in KB)
        max_bytes = spec['max_size'] * 1024
        min_quality = 10
        max_quality = 95
        best_quality = min_quality
        best_data = None

        # Binary search for best JPEG quality so that Huffman-compressed image is <= max_size
        low, high = min_quality, max_quality
        while low <= high:
            quality = (low + high) // 2
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality)
            output.seek(0)
            img_bytes = output.read()
            huff_data = huffman_compress(np.frombuffer(img_bytes, dtype=np.uint8))
            if len(huff_data) <= max_bytes:
                best_quality = quality
                best_data = img_bytes
                low = quality + 1   # Try higher quality
            else:
                high = quality - 1  # Lower quality

        # If none found under max_size, fall back to lowest quality
        if best_data is None:
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=min_quality)
            output.seek(0)
            best_data = output.read()

        # Return the JPEG image (not the Huffman-compressed data, as that's not an image)
        return send_file(
            io.BytesIO(best_data),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f'exam_photo_{exam_type}.jpg'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
