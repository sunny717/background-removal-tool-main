import io
import os
import sys
from flask import Flask, request, send_file, jsonify
from flask.helpers import url_for
from flask_cors import CORS
from PIL import Image
import numpy as np
import time
import logging
import requests
import u2net
import base64
logging.basicConfig(level=logging.INFO)

# Initialize the Flask application
app = Flask(__name__)
CORS(app)


# Simple probe.
@app.route('/', methods=['GET'])
def hello():
    return '<h1>Background Removal API</h1>'


# Route http posts to this method
@app.route('/removebg', methods=['POST'])
def run():
    start = time.time()

    # Convert string of image data to uint8
    if 'data' not in request.files:
        return jsonify({'error': 'missing file param `data`'}), 400
    data = request.files['data'].read()
    if len(data) == 0:
        return jsonify({'error': 'empty image'}), 400

    # Convert string data to PIL Image
    img = Image.open(io.BytesIO(data))

    # Ensure i,qge size is under 1024
    if img.size[0] > 1024 or img.size[1] > 1024:
        img.thumbnail((1024, 1024))

    img_bg_removed = remove_bg(img)

    # Save to buffer
    buff = io.BytesIO()
    img_bg_removed.save(buff, 'PNG')
    buff.seek(0)

    # Print stats
    logging.info(f'Completed in {time.time() - start:.2f}s')
    res_dict={}
    res_dict["code"] = 1
    res_dict["msg"] = "执行成功"
    res_dict["data"]= base64.b64encode(buff.getvalue()).decode("utf-8")

    # Return data
    # return send_file(buff, mimetype='image/png')
    return base64.b64encode(buff.getvalue()).decode("utf-8")


def remove_bg(img):
    # Process Image
    mask = u2net.run(np.array(img)).convert("L")
    bgColor = (255, 255, 255, 255)
    if (request.form.get("backgroundColor") == '蓝色'):
        bgColor = (71, 151, 221, 255)
    elif (request.form.get("backgroundColor") == '红色'):
        bgColor = (200, 44, 59, 255)
    elif (request.form.get("backgroundColor") == '白色'):
        bgColor = (255, 255, 255, 255)
    elif (request.form.get("backgroundColor") == '透明'):
        bgColor = 0
    img_bg_removed = naive_cutout(img, mask, bgColor)
    return img_bg_removed


# Route http posts to this method


@app.route('/removebgmask', methods=['POST'])
def runMask():
    start = time.time()

    # Convert string of image data to uint8
    if 'data' not in request.files:
        return jsonify({'error': 'missing file param `data`'}), 400
    data = request.files['data'].read()
    if len(data) == 0:
        return jsonify({'error': 'empty image'}), 400

    # Convert string data to PIL Image
    img = Image.open(io.BytesIO(data))

    # Ensure i,qge size is under 1024
    if img.size[0] > 1024 or img.size[1] > 1024:
        img.thumbnail((1024, 1024))

    # Process Image
    mask = u2net.run(np.array(img)).convert("L")

    # Save to buffer
    buff = io.BytesIO()
    mask.save(buff, 'PNG')
    buff.seek(0)

    # Print stats
    logging.info(f'Completed in {time.time() - start:.2f}s')

    # Return data
    return send_file(buff, mimetype='image/png')



def naive_cutout(img, mask,bgColor=0):
    empty = Image.new("RGBA", (img.size),bgColor)
    cutout = Image.composite(img, empty, mask.resize(img.size, Image.LANCZOS))
    return cutout


def backgroundRemoval(image_path, fromUrl=False, showOutput=False):
    start = time.time()

    # Get original dataset 
    if not(fromUrl):
        img = Image.open(image_path)
    else:
        img = Image.open(requests.get(image_path, stream=True).raw)

    # Process Image
    mask = u2net.run(np.array(img)).convert("L")

    # masking
    img_bg_removed = naive_cutout(img, mask)
    if showOutput:
        img_bg_removed.show()
    else:
        img_bg_removed.save("./output_dataset_png/"+image_path.split(".")[0]+".png")

    ## convert to JPG
    #img_bg_removed = img_bg_removed.convert('RGB') 

    # Print stats
    logging.info(f'{image_path} Completed in {time.time() - start:.2f}s')

def manualRemoval(url=None, fromUrl=False):
    start = time.time()
    if url == None:
        images_paths = os.listdir("./original_dataset")
        for image_path in images_paths:
            backgroundRemoval("./original_dataset/"+image_path)
    else:
        backgroundRemoval(url, fromUrl, True)
    
    logging.info(f'{len(images_paths)} images done! in {time.time() - start:.2f}s')



if __name__ == '__main__':
    manual = len(sys.argv) >= 2

    if manual:
        fromUrl = sys.argv[1][:4] == 'http'
        manualRemoval(url=sys.argv[1], fromUrl=fromUrl)
    else:
        os.environ['FLASK_ENV'] = 'development'
        port = int(os.environ.get('PORT', 8081))
        app.run(debug=True, host='localhost', port=port)

    
