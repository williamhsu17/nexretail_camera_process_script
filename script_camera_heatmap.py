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

    print("----------\n")


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

def process_camera_heatmap_data(date: str, location: str) -> bool:
    try:
        # Load configuration from a JSON file
        config_path = "config.json"

        with open(config_path, "r") as config_file:
            config = json.load(config_file)

        location_id = config["locations"][location]["LOCATION"]
        CAMERA = config["locations"][location]["heatmap_camera"]
        CAMERA_ID = config["locations"][location]["heatmap_camera_id"]

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
        # print(data)

        print("mask_path: ", MASK_PATH)

        for camera in CAMERA:
            print(f"creating heatmap for cam_2 on {date}.....")

            if MASK_PATH == "mask_新莊":
                if camera == "cam002":
                    xy_values_1 = data['cam_2']['cam_2_YARIS_CROSS']
                    xy_values = np.vstack((xy_values_1))
                    image_path = "csv/mask_新莊/raw_cam_2.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam003":
                    xy_values_1 = data['cam_3']['cam_3_bZ4x']
                    xy_values_2 = data['cam_3']['cam_3_RAV4']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_新莊/raw_cam_3.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam004":
                    xy_values_1 = data['cam_4']['cam_4_VIOS']
                    xy_values = np.vstack((xy_values_1))
                    image_path = "csv/mask_新莊/raw_cam_4.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam005":
                    xy_values_1 = data['cam_5']['cam_5_car_None']
                    xy_values_2 = data['cam_5']['cam_5_SIENTA']
                    xy_values_3 = data['cam_5']['cam_5_COROLLA_SPORT']
                    xy_values = np.vstack((xy_values_1, xy_values_2, xy_values_3))
                    image_path = "csv/mask_新莊/raw_cam_5.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam_6']['cam_6_ALTIS']
                    xy_values_2 = data['cam_6']['cam_6_SIENTA']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_新莊/raw_cam_6.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            elif MASK_PATH == "mask_新竹":
                # 新竹
                if camera == "cam002":
                    xy_values_1 = data['cam_2']['cam_2_car_white']
                    xy_values_2 = data['cam_2']['cam_2_YARIS_CROSS']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_新竹/raw_cam_2.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam003":
                    xy_values_1 = data['cam_3']['cam_3_bZ4x']
                    xy_values_2 = data['cam_3']['cam_3_RAV4']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_新竹/raw_cam_3.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam004":
                    xy_values_1 = data['cam_4']['cam_4_VIOS']
                    xy_values = np.vstack((xy_values_1))
                    image_path = "csv/mask_新竹/raw_cam_4.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam_5']['cam_5_SIENTA']
                    xy_values_2 = data['cam_5']['cam_5_COROLLA_SPORT']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_新竹/raw_cam_5.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam007":
                    xy_values_1 = data['cam_6']['cam_6_SIENTA']
                    xy_values = np.vstack((xy_values_1))
                    image_path = "csv/mask_新竹/raw_cam_6.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            elif MASK_PATH == "mask_西台南":
                # 西台南
                if camera == "cam002":
                    xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
                    xy_values_2 = data['cam002']['cam002_bZ4x']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_西台南/raw_cam002.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam003":
                    xy_values_1 = data['cam003']['cam003_RAV4']
                    xy_values = np.vstack((xy_values_1))
                    image_path = "csv/mask_西台南/raw_cam003.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam004":
                    xy_values_1 = data['cam004']['cam004_VIOS']
                    xy_values_2 = data['cam004']['cam004_VIOS2']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_西台南/raw_cam004.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam005":
                    xy_values_1 = data['cam005']['cam005_SIENTA']
                    xy_values_2 = data['cam005']['cam005_COROLLA_SPORT']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_西台南/raw_cam005.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam006']['cam006_SIENTA']
                    xy_values_2 = data['cam006']['cam006_ALTIS']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_西台南/raw_cam006.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            elif MASK_PATH == "mask_鳳山":
                if camera == "cam002":
                    xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
                    xy_values = np.vstack((xy_values_1))
                    image_path = "csv/mask_鳳山/raw_cam002.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam003":
                    xy_values_1 = data['cam003']['cam003_RAV4']
                    xy_values = np.vstack((xy_values_1))
                    image_path = "csv/mask_鳳山/raw_cam003.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam004":
                    xy_values_1 = data['cam004']['cam004_VIOS']
                    xy_values_2 = data['cam004']['cam004_VIOS2']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_鳳山/raw_cam004.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam005":
                    xy_values_1 = data['cam005']['cam005_COROLLA_SPORT']
                    xy_values_2 = data['cam005']['cam005_SIENTA']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_鳳山/raw_cam005.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam006']['cam006_SIENTA2']
                    xy_values_2 = data['cam006']['cam006_SIENTA3']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_鳳山/raw_cam006.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            elif MASK_PATH == "mask_中台中":
                if camera == "cam002":
                    xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
                    xy_values_2 = data['cam002']['cam002_COROLLA_CROSS']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_中台中/raw_cam002.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam003":
                    xy_values_1 = data['cam003']['cam003_RAV4']
                    xy_values_2 = data['cam003']['cam003_bZ4x']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_中台中/raw_cam003.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam005":
                    xy_values_1 = data['cam005']['cam005_COROLLA_SPORT']
                    xy_values_2 = data['cam005']['cam005_SIENTA']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_中台中/raw_cam005.jpg"
                    cam_image = Image.open(image_path).convert("RGB")

                elif camera == "cam006":
                    xy_values_1 = data['cam006']['cam006_SIENTA2']
                    xy_values_2 = data['cam006']['cam006_VIOS']
                    xy_values = np.vstack((xy_values_1, xy_values_2))
                    image_path = "csv/mask_中台中/raw_cam006.jpg"
                    cam_image = Image.open(image_path).convert("RGB")
            
            elif location == "新店":
                # 新竹
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

            image_path = plot_heatmap(x, y, camera, date, location, cam_image)

            camera_id = CAMERA_ID[CAMERA.index(camera)]
            upload_image(image_path, camera_id, date)
        
        print("")
        print(f"--------------------End Creating Camera Heatmap { date } --------------------")

        return True
        
    except Exception as e:
        print(f"Error processing car plate data: {e}")
        return False

if __name__ == "__main__":
    date = "2025-12-14"
        
    # location = "新莊"
    # location = "新竹"
    # location = "西台南"
    # location = "鳳山"
    location = "中台中"
    # location = "新店"

    process_camera_heatmap_data(date, location)

    # # Load configuration from a JSON file
    # config_path = "config.json"

    # with open(config_path, "r") as config_file:
    #     config = json.load(config_file)

    # location_id = config["locations"][location]["LOCATION"]
    # CAMERA = config["locations"][location]["heatmap_camera"]
    # CAMERA_ID = config["locations"][location]["heatmap_camera_id"]

    # MASK_PATH = f"mask_{location}"

    # print("Processing data...")

    # dx_base_text = {}
    # dx_entrance = {}

    # print(f"processing data for {date}...")
    # data_path = f"output/{location}/{date}"

    # data_base_path = f"{data_path}/{date}_combined_base_text.csv"
    # data_entrance_path = f"{data_path}/{date}_combined_entrance.csv"

    # df_base_text = pd.read_csv(data_base_path)
    # df_entrance = pd.read_csv(data_entrance_path)

    # df_base_text = df_base_text[df_base_text['id'].isin(df_entrance['track_id'])]

    # df_base_text['cx'] = (df_base_text['x1'] + df_base_text['x2']) / 2
    # # df_base_text['cx'] = df_base_text['x1']
    # df_base_text['cy'] = df_base_text['y2']

    # dx_base_text[date] = df_base_text
    # dx_entrance[date] = df_entrance

    # # ====================================================================================================
    # file_path = f'csv/{MASK_PATH}/solutions_masks.npy'
    # data = np.load(file_path, allow_pickle=True).item()
    # # print(data)

    # print("mask_path: ", MASK_PATH)

    # for camera in CAMERA:
    #     print(f"creating heatmap for cam_2 on {date}.....")

    #     if MASK_PATH == "mask_新莊":
    #         if camera == "cam002":
    #             xy_values_1 = data['cam_2']['cam_2_YARIS_CROSS']
    #             xy_values = np.vstack((xy_values_1))
    #             image_path = "csv/mask_新莊/raw_cam_2.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam003":
    #             xy_values_1 = data['cam_3']['cam_3_bZ4x']
    #             xy_values_2 = data['cam_3']['cam_3_RAV4']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_新莊/raw_cam_3.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam004":
    #             xy_values_1 = data['cam_4']['cam_4_VIOS']
    #             xy_values = np.vstack((xy_values_1))
    #             image_path = "csv/mask_新莊/raw_cam_4.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam005":
    #             xy_values_1 = data['cam_5']['cam_5_car_None']
    #             xy_values_2 = data['cam_5']['cam_5_SIENTA']
    #             xy_values_3 = data['cam_5']['cam_5_COROLLA_SPORT']
    #             xy_values = np.vstack((xy_values_1, xy_values_2, xy_values_3))
    #             image_path = "csv/mask_新莊/raw_cam_5.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam006":
    #             xy_values_1 = data['cam_6']['cam_6_ALTIS']
    #             xy_values_2 = data['cam_6']['cam_6_SIENTA']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_新莊/raw_cam_6.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")
        
    #     elif MASK_PATH == "mask_新竹":
    #         # 新竹
    #         if camera == "cam002":
    #             xy_values_1 = data['cam_2']['cam_2_car_white']
    #             xy_values_2 = data['cam_2']['cam_2_YARIS_CROSS']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_新竹/raw_cam_2.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam003":
    #             xy_values_1 = data['cam_3']['cam_3_bZ4x']
    #             xy_values_2 = data['cam_3']['cam_3_RAV4']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_新竹/raw_cam_3.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam004":
    #             xy_values_1 = data['cam_4']['cam_4_VIOS']
    #             xy_values = np.vstack((xy_values_1))
    #             image_path = "csv/mask_新竹/raw_cam_4.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam006":
    #             xy_values_1 = data['cam_5']['cam_5_SIENTA']
    #             xy_values_2 = data['cam_5']['cam_5_COROLLA_SPORT']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_新竹/raw_cam_5.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam007":
    #             xy_values_1 = data['cam_6']['cam_6_SIENTA']
    #             xy_values = np.vstack((xy_values_1))
    #             image_path = "csv/mask_新竹/raw_cam_6.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")
        
    #     elif MASK_PATH == "mask_西台南":
    #         # 西台南
    #         if camera == "cam002":
    #             xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
    #             xy_values_2 = data['cam002']['cam002_bZ4x']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_西台南/raw_cam002.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam003":
    #             xy_values_1 = data['cam003']['cam003_RAV4']
    #             xy_values = np.vstack((xy_values_1))
    #             image_path = "csv/mask_西台南/raw_cam003.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam004":
    #             xy_values_1 = data['cam004']['cam004_VIOS']
    #             xy_values_2 = data['cam004']['cam004_VIOS2']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_西台南/raw_cam004.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam005":
    #             xy_values_1 = data['cam005']['cam005_SIENTA']
    #             xy_values_2 = data['cam005']['cam005_COROLLA_SPORT']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_西台南/raw_cam005.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam006":
    #             xy_values_1 = data['cam006']['cam006_SIENTA']
    #             xy_values_2 = data['cam006']['cam006_ALTIS']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_西台南/raw_cam006.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")
        
    #     elif MASK_PATH == "mask_鳳山":
    #         if camera == "cam002":
    #             xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
    #             xy_values = np.vstack((xy_values_1))
    #             image_path = "csv/mask_鳳山/raw_cam002.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam003":
    #             xy_values_1 = data['cam003']['cam003_RAV4']
    #             xy_values = np.vstack((xy_values_1))
    #             image_path = "csv/mask_鳳山/raw_cam003.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam004":
    #             xy_values_1 = data['cam004']['cam004_VIOS']
    #             xy_values_2 = data['cam004']['cam004_VIOS2']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_鳳山/raw_cam004.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam005":
    #             xy_values_1 = data['cam005']['cam005_COROLLA_SPORT']
    #             xy_values_2 = data['cam005']['cam005_SIENTA']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_鳳山/raw_cam005.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam006":
    #             xy_values_1 = data['cam006']['cam006_SIENTA2']
    #             xy_values_2 = data['cam006']['cam006_SIENTA3']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_鳳山/raw_cam006.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")
        
    #     elif MASK_PATH == "mask_中台中":
    #         if camera == "cam002":
    #             xy_values_1 = data['cam002']['cam002_YARIS_CROSS']
    #             xy_values_2 = data['cam002']['cam002_COROLLA_CROSS']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_中台中/raw_cam002.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam003":
    #             xy_values_1 = data['cam003']['cam003_RAV4']
    #             xy_values_2 = data['cam003']['cam003_bZ4x']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_中台中/raw_cam003.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam005":
    #             xy_values_1 = data['cam005']['cam005_COROLLA_SPORT']
    #             xy_values_2 = data['cam005']['cam005_SIENTA']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_中台中/raw_cam005.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam006":
    #             xy_values_1 = data['cam006']['cam006_SIENTA2']
    #             xy_values_2 = data['cam006']['cam006_VIOS']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_中台中/raw_cam006.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")
        
    #     elif MASK_PATH == "mask_新店":
    #         # 新竹
    #         if camera == "cam002":
    #             xy_values_1 = data['cam002']['cam002_bZ4x']
    #             xy_values_2 = data['cam002']['cam002_YARIS_CROSS']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_新店/raw_cam002.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam004":
    #             xy_values_1 = data['cam004']['cam004_VIOS']
    #             xy_values_2 = data['cam004']['cam004_RAV4']
    #             xy_values = np.vstack((xy_values_1, xy_values_2))
    #             image_path = "csv/mask_新店/raw_cam004.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam005":
    #             xy_values_1 = data['cam005']['cam005_ALTIS']
    #             xy_values_2 = data['cam005']['cam005_COROLLA_CROSS']
    #             xy_values_3 = data['cam005']['cam005_COROLLA_SPORT']
    #             xy_values_4 = data['cam005']['cam005_ALTIS2']
    #             xy_values = np.vstack((xy_values_1, xy_values_2, xy_values_3, xy_values_4))
    #             image_path = "csv/mask_新店/raw_cam005.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #         elif camera == "cam006":
    #             xy_values_1 = data['cam006']['cam006_SIENTA']
    #             xy_values = np.vstack((xy_values_1))
    #             image_path = "csv/mask_新店/raw_cam006.jpg"
    #             cam_image = Image.open(image_path).convert("RGB")

    #     df_region = pd.DataFrame(xy_values, columns=['x', 'y'])

    #     dx_base_text_this_camera = {
    #         date: dx_base_text[date][dx_base_text[date]['camera'] == camera]
    #         for date in dx_base_text
    #     }

    #     df_base_text_combined = pd.concat(dx_base_text_this_camera.values(), ignore_index=True)

    #     df_base_text_combined = df_base_text_combined[
    #         df_base_text_combined[['cx', 'cy']].apply(tuple, axis=1).isin(df_region[['x', 'y']].apply(tuple, axis=1))
    #     ]

    #     x = df_base_text_combined['cx']
    #     y = df_base_text_combined['cy']

    #     plot_heatmap(x, y, camera, date, cam_image)