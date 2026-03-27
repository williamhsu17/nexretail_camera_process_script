import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

from PIL import Image
from scipy.ndimage import gaussian_filter
import requests

AGE_MAP = {
    0: "0-15",
    1: "16-30",
    2: "31-45",
    3: "46-60",
    4: "61-"
}
GENDER_MAP = {
    0: "Male",
    1: "Female"
}
def upload_image(file_path, camera, date):
    url = "https://nexretail-camera-station-v2.de.r.appspot.com/heatmaps/create/"
    
    files = {'image': (os.path.basename(file_path), open(file_path, 'rb'), 'image/jpeg')}
    data = {
        'name': "",
        'date': date,
        'camera': camera
    }
    response = requests.post(url, files=files, data=data)
    if response.status_code == 201:
        print(f"Successfully uploaded {file_path}")
    else:
        print(f"Failed to upload {file_path}. Error: {response.text}")

def plot_heatmap(x, y, camera, date, location, cam_image, age='all', gender='all', sigma=16, vmin=0, vmax=3, alpha=0.6):
    cmap = plt.get_cmap('jet')
    cmap.set_under(color=(1, 1, 1, 0))

    cam_width, cam_height = cam_image.size

    heatmap, xedges, yedges = np.histogram2d(x, y, bins=(cam_width // 2, cam_height // 2), range=[[0, cam_width], [0, cam_height]])

    heatmap_smoothed = gaussian_filter(heatmap, sigma=sigma)

    threshold = 0.01
    # heatmap_smoothed_filtered = np.where(heatmap_smoothed >= threshold, heatmap_smoothed, 0)
    heatmap_smoothed_filtered = np.ma.masked_less(heatmap_smoothed, threshold)

    # lower_bound = 0.3
    # heatmap_masked = np.ma.masked_where(heatmap_smoothed < lower_bound, heatmap_smoothed)
    print("plotting...")
    plt.figure(figsize=(10, 6))
    plt.imshow(cam_image)
    plt.imshow(cam_image, extent=[0, cam_width, 0, cam_height], aspect='auto')
    plt.imshow(heatmap_smoothed_filtered.T, extent=[0, cam_width, 0, cam_height], origin='upper', cmap=cmap, vmin=vmin, vmax=vmax, alpha=alpha)
    plt.xticks([])
    plt.yticks([])
    cbar = plt.colorbar(orientation='horizontal', pad=0.05, aspect=50, shrink=0.8)
    cbar.set_label('Density')
    plt.title(f"heatmap({camera}_{date}_{age}_{gender})")
    # plt.show()

    print(f"saving image...heatmap({camera}_{date}_{age}_{gender})")
    output_directory = f"output/heatmap/{location}/{date}"
    os.makedirs(output_directory, exist_ok=True)
    output_file_path = os.path.join(output_directory, f"{location}_{camera}_{date}_{age}_{gender}.png")
    plt.savefig(output_file_path, dpi=300, bbox_inches='tight')

    plt.close()

    return output_file_path

def process_camera_heatmap_data(date: str, location: str, config_path: str = "config.json") -> bool:
    try:
        # Load configuration from a JSON file

        with open(config_path, "r") as config_file:
            config = json.load(config_file)

        location_id = config["locations"][location]["LOCATION"]
        CAMERA = config["locations"][location]["heatmap_camera"]
        CAMERA_ID = config["locations"][location]["heatmap_camera_id"]


        print(f"--------------------Start Creating Camera {location}({location_id}) Heatmap { date } --------------------")
        
        print("CAMERA: ", CAMERA)
        print("CAMERA_ID: ", CAMERA_ID)

        # Check if the mask file exists, and set MASK_PATH accordingly
        mask_file_path = f"csv/{location}/{date}/{date}T09_00_00/labels/solutions_masks.npy"
        if os.path.exists(mask_file_path):
            MASK_PATH = f"{location}/{date}/{date}T09_00_00/labels"
            print(f"daily mask path found: {MASK_PATH}")
        else:
            MASK_PATH = f"mask_{location}"
            print(f"using default mask path: {MASK_PATH}.")

        # MASK_PATH = f"mask_{location}"
        # print(f"Using mask path: {MASK_PATH}")

        print("Processing data...")

        dx_base_text = {}
        dx_entrance = {}

        print(f"processing data for {date}...")
        data_path = f"output/{location}/{date}"

        data_base_path = f"{data_path}/{date}_combined_base_text.csv"
        data_entrance_path = f"{data_path}/{date}_combined_entrance.csv"

        df_base_text = pd.read_csv(data_base_path)
        df_entrance = pd.read_csv(data_entrance_path)

        df_base_text = df_base_text[df_base_text['id'].isin(df_entrance['track_id'])]

        df_base_text['cx'] = (df_base_text['x1'] + df_base_text['x2']) / 2
        # df_base_text['cx'] = df_base_text['x1']
        df_base_text['cy'] = df_base_text['y2']

        dx_base_text[date] = df_base_text
        dx_entrance[date] = df_entrance

        # ====================================================================================================
        file_path = f'csv/{MASK_PATH}/solutions_masks.npy'
        data = np.load(file_path, allow_pickle=True).item()
        def _print_data_structure(d, indent=0):
            for k, v in d.items():
                prefix = "  " * indent
                if isinstance(v, dict):
                    print(f"{prefix}{k}/")
                    _print_data_structure(v, indent + 1)
                elif isinstance(v, np.ndarray):
                    print(f"{prefix}{k}: ndarray shape={v.shape}, dtype={v.dtype}")
                else:
                    print(f"{prefix}{k}: {type(v).__name__}")

        print("solutions_masks.npy structure:")
        _print_data_structure(data)
        # print(data)

        print("mask_path: ", MASK_PATH)
        print("")

        for camera in CAMERA:
            print(f"creating heatmap for {camera} on {date}.....")

            if location_id == 1:
                print("location_id 1 found, using 新莊 mask settings.")
                if camera == "cam002":
                    xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
                    xy_values = np.vstack((xy_values_1))
                    image_path = f"csv/{MASK_PATH}/raw_cam002.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                # elif camera == "cam003":
                #     xy_values_1 = data['cam003']['cam003_bZ4x']
                #     xy_values_2 = data['cam003']['cam003_RAV4']
                #     xy_values = np.vstack((xy_values_1, xy_values_2))
                #     image_path = "csv/mask_新莊/raw_cam_3.jpg"
                #     cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam004":
                    xy_values_1 = data['cam004']['cam004_VIOS']
                    xy_values = np.vstack((xy_values_1))
                    image_path = f"csv/{MASK_PATH}/raw_cam004.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam005":
                    xy_values_1 = data['cam005']['cam005_car_None']
                    xy_values_2 = data['cam005']['cam005_SIENTA']
                    xy_values_3 = data['cam005']['cam005_COROLLA_SPORT']
                    xy_values = np.vstack((xy_values_1, xy_values_2, xy_values_3))
                    image_path = f"csv/{MASK_PATH}/raw_cam005.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam006']['cam006_ALTIS']
                    xy_values_2 = data['cam006']['cam006_SIENTA']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam006.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            # elif MASK_PATH == "mask_新竹":
            elif location_id == 2:
                print("location_id 2 found, using 新竹 mask settings.")
                # 新竹
                if camera == "cam002":
                    xy_values_1 = data['cam002']['cam002_car_white']
                    xy_values_2 = data['cam002']['cam002_YARIS_CROSS']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam002.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam003":
                    xy_values_1 = data['cam003']['cam003_bZ4x']
                    xy_values_2 = data['cam003']['cam003_RAV4']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam003.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam004":
                    xy_values_1 = data['cam004']['cam004_VIOS']
                    xy_values = np.vstack((xy_values_1))
                    image_path = f"csv/{MASK_PATH}/raw_cam004.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam006']['cam006_SIENTA']
                    xy_values_2 = data['cam006']['cam006_COROLLA_SPORT']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam006.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam007":
                    xy_values_1 = data['cam007']['cam007_SIENTA']
                    xy_values = np.vstack((xy_values_1))
                    image_path = f"csv/{MASK_PATH}/raw_cam007.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            elif location_id == 3:
                print("location_id 3 found, using 西台南 mask settings.")
                # 西台南
                if camera == "cam002":
                    xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
                    xy_values_2 = data['cam002']['cam002_bZ4x']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam002.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam003":
                    xy_values_1 = data['cam003']['cam003_RAV4']
                    xy_values = np.vstack((xy_values_1))
                    image_path = f"csv/{MASK_PATH}/raw_cam003.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam004":
                    xy_values_1 = data['cam004']['cam004_VIOS']
                    xy_values_2 = data['cam004']['cam004_VIOS2']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam004.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam005":
                    xy_values_1 = data['cam005']['cam005_SIENTA']
                    xy_values_2 = data['cam005']['cam005_COROLLA_SPORT']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam005.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam006']['cam006_SIENTA']
                    xy_values_2 = data['cam006']['cam006_ALTIS']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam006.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            # elif MASK_PATH == "mask_鳳山":
            elif location_id == 4:
                print("location_id 4 found, using 鳳山 mask settings.")
                if camera == "cam002":
                    xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
                    xy_values = np.vstack((xy_values_1))
                    image_path = f"csv/{MASK_PATH}/raw_cam002.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam003":
                    xy_values_1 = data['cam003']['cam003_RAV4']
                    xy_values = np.vstack((xy_values_1))
                    image_path = f"csv/{MASK_PATH}/raw_cam003.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam004":
                    xy_values_1 = data['cam004']['cam004_VIOS']
                    xy_values_2 = data['cam004']['cam004_VIOS2']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam004.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam005":
                    xy_values_1 = data['cam005']['cam005_COROLLA_SPORT']
                    xy_values_2 = data['cam005']['cam005_SIENTA']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam005.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam006']['cam006_SIENTA2']
                    xy_values_2 = data['cam006']['cam006_SIENTA3']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam006.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            # elif MASK_PATH == "mask_中台中":
            elif location_id == 5:
                print("location_id 5 found, using 中台中 mask settings.")
                if camera == "cam002":
                    xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
                    xy_values_2 = data['cam002']['cam002_COROLLA_CROSS']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam002.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam003":
                    xy_values_1 = data['cam003']['cam003_RAV4']
                    xy_values_2 = data['cam003']['cam003_bZ4x']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam003.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam005":
                    xy_values_1 = data['cam005']['cam005_COROLLA_SPORT']
                    xy_values_2 = data['cam005']['cam005_SIENTA']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam005.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam006']['cam006_SIENTA2']
                    xy_values_2 = data['cam006']['cam006_VIOS']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam006.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            # elif location == "新店":
            elif location_id == 6:
                print("location_id 6 found, using 新店 mask settings.")
                # 新店
                if camera == "cam002":
                    xy_values_1 = data['cam002']['cam002_bZ4x']
                    xy_values_2 = data['cam002']['cam002_YARIS_CROSS']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam002.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam004":
                    xy_values_1 = data['cam004']['cam004_VIOS']
                    xy_values_2 = data['cam004']['cam004_RAV4']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = f"csv/{MASK_PATH}/raw_cam004.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam005":
                    xy_values_1 = data['cam005']['cam005_ALTIS']
                    xy_values_2 = data['cam005']['cam005_COROLLA_CROSS']
                    xy_values_3 = data['cam005']['cam005_COROLLA_SPORT']
                    xy_values_4 = data['cam005']['cam005_ALTIS2']
                    xy_values = np.vstack((xy_values_1, xy_values_2, xy_values_3, xy_values_4))
                    image_path = f"csv/{MASK_PATH}/raw_cam005.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam006']['cam006_SIENTA']
                    xy_values = np.vstack((xy_values_1))
                    image_path = f"csv/{MASK_PATH}/raw_cam006.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

            df_region = pd.DataFrame(xy_values, columns=['x', 'y'])

            dx_base_text_this_camera = {
                date: dx_base_text[date][dx_base_text[date]['camera'] == camera]
                for date in dx_base_text
            }

            df_base_text_combined = pd.concat(dx_base_text_this_camera.values(), ignore_index=True)

            df_base_text_combined = df_base_text_combined[
                df_base_text_combined[['cx', 'cy']].apply(tuple, axis=1).isin(df_region[['x', 'y']].apply(tuple, axis=1))
            ]

            x = df_base_text_combined['cx']
            y = df_base_text_combined['cy']

            print("camera: ", camera)

            image_path = plot_heatmap(x, y, camera, date, location, cam_image)

            camera_id = CAMERA_ID[CAMERA.index(camera)]
            upload_image(image_path, camera_id, date)
            print("----------\n")
        
        print(f"--------------------End   Creating Camera {location}({location_id}) Heatmap { date } --------------------")
        print("")

        return True
        
    except Exception as e:
        print(f"Error processing car plate data: {e}")
        return False

if __name__ == "__main__":
    date_stamps = [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
        "2026-01-04",
        "2026-01-05",
        "2026-01-06",
        "2026-01-07",
        # "2026-01-08",
        # "2026-01-09",
        # "2026-01-10",
        # "2026-01-11",
        # "2026-01-12",
        # "2026-01-13",
        # "2026-01-14",
        # "2026-01-15",
        # "2026-01-16",
        # "2026-01-17",
        # "2026-01-18",
        # "2026-01-19",
        # "2026-01-20",
        # "2026-01-21",
        # "2026-01-22",
        # "2026-01-23",
        # "2026-01-24",
        # "2026-01-25",
        # "2026-01-26",
        # "2026-01-27",
        # "2026-01-28",
        # "2026-01-29",
        # "2026-01-30",
        # "2026-01-31",
    ]

    locations = [
        # "新莊",
        # "新竹",
        # "西台南",
        "鳳山",
        # "中台中",
        # "新店",
        # "桃園PIC",
    ]

    for date_stamp in date_stamps:
        for location in locations:
            process_camera_heatmap_data(date_stamp, location)
