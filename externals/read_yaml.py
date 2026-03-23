import re
from collections import OrderedDict
from pathlib import Path
import numpy as np
import pkg_resources
import collections
import subprocess
import shutil
import copy
import json
import yaml
import cv2
import os
import sys
from PIL import Image

sys.path.append(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '..'))

__all__ = ['read_config', 'copyTree', 'imread', 'read_json', 'write_json', 'rmdir',
           'config_to_str', 'array_interweave', 'array_interweave3', 'neq', 'pip_install', 'COLOR']


def read_config(path_config: str, base=True):
    r""" read config yml file, return dict
    """

    def update(d, u):
        r""" deep update dict.
        copied from here: https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
        """
        for k, v in u.items():
            if isinstance(v, collections.abc.Mapping):
                d[k] = update(d.get(k, {}), v)
            if isinstance(v, list):
                return d
            else:
                d[k] = v
        return d

    def deep_merge(config, name):
        new_config = copy.deepcopy(config)
        for key, value in config[name]['default'][config[name]['name']].items():
            if key not in config[name]:
                new_config[name][key] = value
        return new_config
    def expand_cambaseline(config, name):
        new_config = copy.deepcopy(config)
        '''
        for cam, cam_value in config[name].items():
            for key, value in cam_value.items():
                if key in config["operation"]:
                    update_value = update(value, copy.deepcopy(config["operation"][key]))
                    new_config[name][cam][key] = update_value
                else:
                    raise f"In flow count config, {cam}'s {key} operation is not in default"
        '''
        for cam, solutions in config[name].items():
            # for key, value in cam_value.items():
            for i, solution in enumerate(solutions):
                key = solution["operation"]
                if key in config["operation"]:
                    oper = {**config["operation_base"], **config["operation"][key], **solution}
                    update_value = update(solution, copy.deepcopy(oper))
                    new_config[name][cam][i] = copy.deepcopy(oper)#update_value
                else:
                    raise NameError(f"In flow count config, {cam}'s {key} operation is not in default")

        return new_config

    new_config = yaml.safe_load(open(path_config))
    # new_config = expand_cambaseline(new_config, "cam_baseline")
    if not base or new_config.get("base", None) is None:
        return new_config
    base_config = yaml.safe_load(open(new_config['base']))

    all_config = update(base_config, new_config)
    all_config = expand_cambaseline(all_config, "cam_baseline")
    if new_config.get("count_mode"):
        all_config["count_mode"] = new_config["count_mode"]
        all_config = remove_cam(all_config, new_config["count_mode"].keys())
    return all_config


def copyTree(src, dst):
    r""" Move and overwrite files and folders

    Args:
        src (str): [description]
        dst (str): [description]
    """

    def forceMergeFlatDir(srcDir, dstDir):
        if not os.path.exists(dstDir):
            os.makedirs(dstDir)
        for item in os.listdir(srcDir):
            srcFile = os.path.join(srcDir, item)
            dstFile = os.path.join(dstDir, item)
            forceCopyFile(srcFile, dstFile)

    def forceCopyFile(sfile, dfile):
        if os.path.isfile(sfile):
            shutil.copy2(sfile, dfile)

    def isAFlatDir(sDir):
        for item in os.listdir(sDir):
            sItem = os.path.join(sDir, item)
            if os.path.isdir(sItem):
                return False
        return True

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isfile(s):
            if not os.path.exists(dst):
                os.makedirs(dst)
            forceCopyFile(s, d)
        if os.path.isdir(s):
            isRecursive = not isAFlatDir(s)
            if isRecursive:
                copyTree(s, d)
            else:
                forceMergeFlatDir(s, d)


def imread(path, with_cv=True):
    if with_cv:
        image = cv2.imread(path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    else:
        image = Image.open(path).convert('RGB')
    return image


def read_json(fname):
    fname = Path(fname)
    with fname.open('rt') as handle:
        return json.load(handle, object_hook=OrderedDict)


def write_json(content, fname):
    fname = Path(fname)
    with fname.open('wt') as handle:
        json.dump(content, handle, indent=4, sort_keys=False)


def rmdir(path, remove_parent=True):
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    if remove_parent:
        if os.path.exists(path):
            os.rmdir(path)


def config_to_str(config):
    return "{" + "\n".join("{!r}: {!r},".format(k, v) for k, v in config.items()) + "}"


def array_interweave(a, b):
    c = np.empty((a.size + b.size,), dtype=a.dtype)
    c[0::2] = a
    c[1::2] = b
    return c


def array_interweave3(a, b, c):
    d = np.empty((a.size + b.size + c.size,), dtype=a.dtype)
    d[0::3] = a
    d[1::3] = b
    d[2::3] = c
    return d


def neq(x, y, z):
    return (x != y or z) or y != z


def pip_install(package, version=None):
    r""" install package from pip

    Args:
        package (str): name of package
        version (str, optional): version of package. Defaults to None.
    """
    if version is not None:
        if pkg_resources.get_distribution(package).version == version:
            return
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package + "==" + version])
    else:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package])
def update(d, u):
    r""" deep update dict.
    copied from here: https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    """
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update(d.get(k, {}), v)
        else:
            d[k] = v
    return d
def remove_cam(d, preserve_cam=["cam_1"]):
    r""" deep update dict.
    copied from here: https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    """
    def is_recam(s, pre_cam):
        pattern = r"cam_\d+"
        cam = re.match(pattern, s)
        if cam is None: return cam
        if cam[0] in pre_cam:
            return False
        return True
    copy_d = copy.deepcopy(d)
    def remove(d, copy, preserve_cam):
        for k, v in d.items():
            if is_recam(k, preserve_cam):
                del copy[k]
            elif isinstance(v, collections.abc.Mapping):
                remove(v, copy[k], preserve_cam)
    remove(d,copy_d, preserve_cam)
    return copy_d

# 定義從 path 中提取 fid 數字的函數
def get_fid(path):
    match = re.search(r'fid(\d+)', path)
    return int(match.group(1)) if match else float('inf')  # 沒有 fid 就排在最後

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os
import numpy as np
import cv2

def save_gif_from_imglist(imgs_list, save_dir, label="", to_mp4=True, fps=10):
    """
    生成 GIF，選擇性輸出 MP4（H.264 高壓縮）

    imgs_list : 圖片檔案名 list
    save_dir  : 圖片所在資料夾
    label     : 顯示的標籤文字
    to_mp4    : 是否輸出 MP4
    fps       : MP4 幀率
    """
    if len(imgs_list) < 2:
        print(f"images list is too short: {len(imgs_list)}")
        return imgs_list
    
    # 讀取並排序
    sort_img = sorted(imgs_list, key=get_fid)
    images = []
    for f in sort_img:
        img = Image.open(os.path.join(save_dir, f))
        images.append(img.copy())
        img.close()
    
    # 調整尺寸
    imgs_size = np.array([list(img.size) for img in images])
    resize_size = tuple(imgs_size[0]) if np.all(imgs_size == imgs_size[0]) else (128, 256)
    resized_images = [img.resize(resize_size) for img in images]
    
    # 加上上方黑底白字區域
    total = len(resized_images)
    font = ImageFont.load_default()
    
    annotated_images = []
    for idx, img in enumerate(resized_images, start=1):
        text = f"{idx}/{total} {label}" if label else f"{idx}/{total}"
        bbox = font.getbbox(text)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        padding_v = 5
        bar_height = text_h + padding_v * 2
        
        # 建立新圖像（上方黑底 + 原圖）
        new_img = Image.new("RGB", (img.width, img.height + bar_height), color="black")
        new_img.paste(img, (0, bar_height))
        
        # 在黑色區域置中繪製文字
        draw = ImageDraw.Draw(new_img)
        text_x = (img.width - text_w) // 2
        text_y = (bar_height - text_h) // 2
        draw.text((text_x, text_y), text, font=font, fill="white")
        
        annotated_images.append(new_img)
    
    # 建立 gif 輸出資料夾
    save_path = Path(imgs_list[0]).with_suffix('.gif')
    gif_dir = save_path.parent.parent / "gif"
    (Path(save_dir) / gif_dir).mkdir(parents=True, exist_ok=True)
    save_path = gif_dir / save_path.name
        # 儲存 MP4（cv2 寫法）
    if to_mp4:
        mp4_path = Path(save_path).with_suffix('.mp4')
        mp4_fullpath = os.path.join(save_dir, str(mp4_path))
        
        h, w = annotated_images[0].size[1], annotated_images[0].size[0]  # PIL size=(w,h)
        fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264
        out = cv2.VideoWriter(mp4_fullpath, fourcc, fps, (w, h))
        
        for img in annotated_images:
            frame_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            out.write(frame_bgr)
        out.release()
        outputs = [str(mp4_path)]

    else:
            # 儲存 GIF
        final_images = [img.convert('P') for img in annotated_images]
        final_images[0].save(
            os.path.join(save_dir, str(save_path)),
            save_all=True,
            append_images=final_images[1:],
            duration=int(1000 / fps),  # fps -> 毫秒
            loop=0,
            optimize=True
        )
        outputs = [str(save_path)]

    return outputs


class COLOR:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
