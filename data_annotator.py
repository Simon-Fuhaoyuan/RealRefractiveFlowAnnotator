import json
import argparse
import os
import cv2
import numpy as np
from labelme.utils import shape_to_mask


def parse_args():
    parser = argparse.ArgumentParser(description='Arguments for annotating transparent photos.')
    parser.add_argument('stage', type=int)
    parser.add_argument('--image_dir', type=str, default='image_0')
    parser.add_argument('--crop_dir', type=str, default='crop_imgs')
    parser.add_argument('--graycode_dir', type=str, default='graycode_imgs')
    parser.add_argument('--crop_json', type=str, default='crop.json')
    parser.add_argument('--mask_json', type=str, default='mask.json')
    parser.add_argument('--width', type=int, default=512)
    parser.add_argument('--height', type=int, default=512)

    config = parser.parse_args()

    return config


def calculate_crop_region(points):
    """Calculate final matting size based on raw annotation data. In the following codes, 'lt' means left_top, 'rt' means 
       right_top, 'lb' means left_bottom, 'rb' means right_bottom.
    Args:
        points: [[lt_x, lt_y], [lb_x, lb_y], [rb_x, rb_y], [rt_x, rt_y]]
    """
    lt_x, lt_y = points[0]
    lb_x, lb_y = points[1]
    rb_x, rb_y = points[2]
    rt_x, rt_y = points[3]

    lt_x_mean = int((lt_x + lb_x) // 2)
    lt_y_mean = int((lt_y + rt_y) // 2)
    rb_x_mean = int((rb_x + rt_x) // 2)
    rb_y_mean = int((lb_y + rb_y) // 2)

    return [[lt_x_mean, lt_y_mean], [rb_x_mean, rb_y_mean]]


def get_annotation(json_file):
    json_str = ''
    with open(json_file, 'r') as f:
        json_str = f.read()
    
    annotation = json.loads(json_str)
    return annotation


def binary_image(img, threshold=120):
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary_img = cv2.threshold(gray_img, threshold, 255, cv2.THRESH_BINARY)

    return binary_img


def generate_mask(image_dir, json_file):
    json_path = os.path.join(image_dir, json_file)    
    annotation = get_annotation(json_path)
    points = annotation['shapes'][0]['points']
    mask = shape_to_mask((512, 512), points)

    return mask


def generate_white():
    white = np.zeros((512, 512))
    white[:, :] = 255
    cv2.imwrite('graycode_512_512/graycode_0.png', white)


def save_mask_image(mask, save_path):
    img = np.zeros(mask.shape)
    img[:, :] = 255
    img[mask] = 0
    cv2.imwrite(save_path, img)


def crop_images(image_dir, crop_dir, json_file):
    json_path = os.path.join(image_dir, json_file)    
    annotation = get_annotation(json_path)
    points = annotation['shapes'][0]['points']
    crop_region = calculate_crop_region(points)

    imgs = os.listdir(image_dir)
    os.makedirs(os.path.join(image_dir, crop_dir), exist_ok=True)

    for img in imgs:
        if not '.png' in img:
            continue
        meta = img[:-10]
        img = os.path.join(image_dir, img)
        img = cv2.imread(img)

        crop_img = img[crop_region[0][1]:crop_region[1][1], crop_region[0][0]:crop_region[1][0]]
        crop_img_resize = cv2.resize(crop_img, (512, 512))
        cv2.imwrite(os.path.join(image_dir, crop_dir, meta + '.png'), crop_img_resize)
    

def generate_graycode(image_dir, crop_dir, gray_code_dir, mask_json):
    json_path = os.path.join(image_dir, mask_json)
    annotation = get_annotation(json_path)

    total_mask = np.zeros((512, 512), dtype=np.bool)
    shapes = annotation['shapes']
    for shape in shapes:
        points = shape['points']
        mask = shape_to_mask((512, 512), points)
        total_mask = np.logical_or(total_mask, mask)

    crop_dir = os.path.join(image_dir, crop_dir)
    gray_code_dir = os.path.join(image_dir, gray_code_dir)
    os.makedirs(gray_code_dir, exist_ok=True)

    # Save mask
    save_mask_image(total_mask, os.path.join(gray_code_dir, '0.png'))

    for i in range(19):
        img = os.path.join(crop_dir, str(i) + '.png')
        img = cv2.imread(img)
        binary_img = binary_image(img)
        
        gray_code = cv2.imread(os.path.join('graycode_512_512', 'graycode_' + str(i) + '.png'))
        gray_code = binary_image(gray_code)
        gray_code[total_mask] = binary_img[total_mask]
        cv2.imwrite(os.path.join(gray_code_dir, str(i + 1) + '.png'), gray_code)


def main(config):
    if config.stage == 1:
        crop_images(
            config.image_dir, 
            config.crop_dir, 
            config.crop_json
        )
    elif config.stage == 2:
        generate_graycode(
            config.image_dir, 
            config.crop_dir, 
            config.graycode_dir, 
            config.mask_json
        )
    else:
        print('Wrong stage!')
        exit(-1)


if __name__ == '__main__':
    config = parse_args()
    main(config)
