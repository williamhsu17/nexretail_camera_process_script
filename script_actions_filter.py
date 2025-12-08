import json
import pandas as pd
from datetime import datetime, timedelta
import requests



import re
from pathlib import Path
import numpy as np
import os
from PIL import Image

AGE_MAP = {
    0: "0-15",
    1: "16-30",
    2: "31-45",
    3: "46-60",
    4: "61-"
}

def summarize_action(actions: list) -> str:
    if "category" in actions:
        return "category"
    elif "document" in actions:
        return "document"
    else:
        return "other"

def calculate_table_head_count(combined_gender) -> int:
    if isinstance(combined_gender, list):
        return len(combined_gender)
    return 1
        
def process_camera_data(file_path: str) -> pd.DataFrame:
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Sort by 'solution' first and then by 'datetime'
    df = df.sort_values(by=['solution', 'datetime'])
    df['actions'] = df['actions'].apply(eval)  # Convert string representation of list to actual list
    
    # Drop rows with no value in gender column
    # df = df.dropna(subset=['gender'])

    # Remove rows with 'staytime' smaller than 500
    df = df[df['staytime'] >= 200]

    df['datetime'] = pd.to_datetime(df['datetime'])

    # Iterate through the DataFrame and remove rows based on the condition
    df["combined_gender"] = ""
    df["combined_age"] = ""
    df["table_head_count"] = ""
    # df["combined_track_id"] = ""

    # rows_to_remove = set()
    # for solution, group in df.groupby('solution'):
    #     for i in range(len(group) - 1):
    #         current_row = group.iloc[i]
    #         next_row = group.iloc[i + 1]
            
    #         staytime_seconds = int(current_row['staytime'])
    #         end_time = current_row['datetime'] + timedelta(seconds=staytime_seconds)
            
    #         if next_row['datetime'] <= end_time:
    #             rows_to_remove.add(next_row.name)

    #             if not current_row['combined_gender']:
    #                 df.at[current_row.name, 'combined_gender'] = [current_row['gender']]
    #                 df.at[current_row.name, 'combined_age'] = [current_row['age']]
    #             df.at[current_row.name, 'combined_gender'].append(next_row['gender'])
    #             df.at[current_row.name, 'combined_age'].append(next_row['age'])
    
    # df.drop(index=rows_to_remove, inplace=True)

    df = df.sort_values(by=['solution', 'datetime'])

    # df['age'] = df['age'].map(AGE_MAP)

    # 進行桌組的組合 - 把以時間序列將不同的object組合成同桌，並把gender和age加入combined欄位，然後把重複的刪掉
    rows_to_remove = set()
    for solution, group in df.groupby('solution'):
        for i in range(len(group) - 1, 0, -1):
            current_row = group.iloc[i]
            prev_row = group.iloc[i - 1]
            
            staytime_seconds = int(prev_row['staytime'])
            end_time = prev_row['datetime'] + timedelta(seconds=staytime_seconds)
            
            if df.at[current_row.name, 'combined_gender'] == "":
                df.at[current_row.name, 'combined_gender'] = [current_row['gender']]
                df.at[current_row.name, 'combined_age'] = [str(current_row['age'])]
                # df.at[current_row.name, 'combined_track_id'] = [str(current_row['track_id'])]

            if current_row['datetime'] <= end_time:
                rows_to_remove.add(current_row.name)

                if df.at[prev_row.name, 'combined_gender'] == "":
                    df.at[prev_row.name, 'combined_gender'] = [prev_row['gender']]
                    df.at[prev_row.name, 'combined_age'] = [str(prev_row['age'])]
                    # df.at[prev_row.name, 'combined_track_id'] = [str(prev_row['track_id'])]
                
                df.at[prev_row.name, 'combined_gender'] = df.at[prev_row.name, 'combined_gender'] + df.at[current_row.name, 'combined_gender']
                df.at[prev_row.name, 'combined_age'] = df.at[prev_row.name, 'combined_age'] + df.at[current_row.name, 'combined_age']
                # df.at[prev_row.name, 'combined_track_id'] = df.at[prev_row.name, 'combined_track_id'] + df.at[current_row.name, 'combined_track_id']
                
                # df.at[prev_row.name, 'combined_gender'].append(current_row['gender'])
                # df.at[prev_row.name, 'combined_age'].append(current_row['age'])
    
    df.drop(index=rows_to_remove, inplace=True)

    # Filter rows based on minutes part of datetime is 00:00
    df = df.sort_values(by=['solution', 'datetime'])
    df["joint_staytime"] = ""
    df["joint_action"] = ""
    
    rows_to_remove = set()
    for solution, group in df.groupby('solution'):
        for i in range(len(group) - 1, 0, -1):
            current_row = group.iloc[i]
            prev_row = group.iloc[i - 1]

            if current_row['datetime'].minute == 0 and current_row['datetime'].second == 0 and i != 0:
                # df.at[prev_row.name, 'joint_action'] = prev_row.actions + current_row.actions
                # df.at[prev_row.name, 'joint_staytime'] = prev_row.staytime + current_row.staytime
                df.at[prev_row.name, 'actions'] = prev_row.actions + current_row.actions
                df.at[prev_row.name, 'staytime'] = prev_row.staytime + current_row.staytime
                rows_to_remove.add(current_row.name)
    
    df.drop(index=rows_to_remove, inplace=True)

    # Filter rows based on 'actions' column
    df["doc_catalog_count"] = ""
    df["action_summary"] = ""
    # df['actions'] = df['actions'].apply(eval)  # Convert string representation of list to actual list
    rows_to_remove = set()
    for i in range(len(df)):
        # print(f"i: {i}")
        current_row = df.iloc[i]
        
        if not any(action in current_row['actions'] for action in ["document", "category", "catalog", "other"]):
            # print(f"no action, removing row {current_row.name}")
            rows_to_remove.add(current_row.name)
        else:
            # Count the number of "document" and "catalog" actions
            doc_catalog_count = sum(action in ["document", "category", "catalog"] for action in current_row['actions'])
            # df.at[current_row.name, 'doc_catalog_count'] = doc_catalog_count
            if doc_catalog_count < 2:
                print(f"less than 2 actions, removing row {current_row.name}")
                rows_to_remove.add(current_row.name)   
    
    df.drop(index=rows_to_remove, inplace=True)

    df['action_summary'] = df['actions'].apply(summarize_action)
    df['table_head_count'] = df['combined_gender'].apply(calculate_table_head_count)

    rows_to_remove = set()
    for i in range(len(df)):
        current_row = df.iloc[i]

        if current_row['table_head_count'] == 1:
            rows_to_remove.add(current_row.name)
    
    df.drop(index=rows_to_remove, inplace=True)

    column_order = ['track_id', 'table_head_count', 'combined_gender', 'gender', 'combined_age', 'age', 'solution', 'action_summary', 'actions', 'img_path', 'staytime', 'datetime', 'Camera', 'Shop']
    df = df[column_order]

    df = df.sort_values(by=['solution', 'datetime'])
    
    return df

# 定義從 path 中提取 fid 數字的函數
def get_fid(path):
    match = re.search(r'fid(\d+)', path)
    return int(match.group(1)) if match else float('inf')  # 沒有 fid 就排在最後

def save_gif_from_imglist(imgs_list, save_dir, target_dir):
    if len(imgs_list)<2:
        return imgs_list

    # 讀取所有圖片
    sort_img = sorted(imgs_list, key=get_fid)
    images = []
    for f in sort_img:
        img = Image.open(os.path.join(save_dir, f))
        images.append(img.copy())
        img.close()

    # 根據 fid 進行排序
    imgs_size = np.array([list(img.size) for img in images])
    resize_size = tuple(imgs_size[0]) if np.all(imgs_size==imgs_size[0]) else (128,256)
    resized_images = [img.resize(resize_size) for img in images]

    save_path = Path(imgs_list[0]).with_suffix('.gif')
    gif_dir = save_path.parent.parent / "gif"
    
    (Path(save_dir)/gif_dir).mkdir(parents=True, exist_ok=True)
    save_path = gif_dir / save_path.name
    # 儲存成 GIF

    # 降低顏色數
    # quantized_images = [img.quantize(colors=64) for img in resized_images]

    # 確保模式
    final_images = [img.convert('P') for img in resized_images]

    # 儲存
    final_images[0].save(
        os.path.join(save_dir, str(save_path)),
        save_all=True,
        append_images=final_images[1:],
        duration=300,
        loop=0,
        optimize=True
    )
    return str(save_path)

def upload(json_payload, url="https://nexretail-camera-station-v2.de.r.appspot.com/data_storage/action_data_upload/"):
    print("uploading action data...")
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json_payload, headers=headers)

    if response.status_code == 201:
        print("\nData uploaded successfully.")
        print("Response message:", response.json().get("message", "No message in response"))

        return response.json().get("action_data_id")
    else:
        print(f"\nFailed to upload data. Status code: {response.status_code}")
        print("Response message:", response.json().get("message", "No message in response"))

def process_action_data(date: str, location: str) -> bool:
    try:
        # Load configuration from a JSON file
        config_path = "config.json"

        with open(config_path, "r") as config_file:
            config = json.load(config_file)

        location_id = config["locations"][location]["LOCATION"]
        if_create_gif = config["locations"][location].get("create_gif_for_action", False)
        print(f"Create GIF for action: {if_create_gif}")

        folder_path = f"output/{location}/{date}"
        file_path = f"{folder_path}/{date}_combined_region_table.csv"

        processed_df = process_camera_data(file_path)
        processed_df["location"] = location_id
        processed_df['datetime'] = processed_df['datetime'].apply(lambda x: str(x))
        processed_df["actions"] = ""

        processed_df["gif_path"] = ""
        gif_folder = os.path.join(folder_path, "gif")
        os.makedirs(gif_folder, exist_ok=True)

        if if_create_gif:
            # 產生 GIF 連結
            for idx, row in processed_df.iterrows():
                this_datetime = pd.to_datetime(row['datetime'])
                this_datetime = this_datetime.strftime("%Y-%m-%dT%H_00_00")

                processed_df.loc[idx, "gif_path"] = save_gif_from_imglist(eval(row['img_path']), f"csv/{location}/{date}/{this_datetime}", f"csv/{location}/{date}/gif")

        processed_df.to_csv(f"{folder_path}/{date}_combined_region_table_filtered.csv", index=False)

        processed_df["img_path"] = ""
        # processed_df["gif_path"] = ""
        json_payload = processed_df.to_json(orient="records")
        # print(json_payload)

        # ----- batchupload -----
        # upload(json_payload)

        # ----- single upload with image -----
        base_directory = f"csv/{location}/{date}/"
        folder_path = f"output/{location}/{date}/"

        # 上傳單筆資料，取得資料id，並上傳對應圖片
        row_count = 1
        for idx, row in processed_df.iterrows():
            print("")
            print("---------------------------------------------------------------")
            row_df = pd.DataFrame([row])
            row_payload = row_df.to_json(orient="records")
            print(f"Uploading row {row_count}/{len(processed_df)}")
            row_count += 1
            print(row_payload)
            action_data_id = upload(row_payload)

            this_datetime = pd.to_datetime(row['datetime'])
            formatted_datetime = this_datetime.strftime("%Y-%m-%dT%H_00_00")

            if if_create_gif:
                # 上傳 GIF 圖片
                image_upload_url = f"https://nexretail-camera-station-v2.de.r.appspot.com/data_storage/action_data_image_upload/{action_data_id}/"
                with open(f"{base_directory}{formatted_datetime}/{row['gif_path']}", 'rb') as img_file:
                    files = {'image': (os.path.basename(f"{base_directory}{formatted_datetime}/{row['gif_path']}"), img_file, 'image/jpeg')}
                    response = requests.post(image_upload_url, files=files)
                    
                    if response.status_code == 201:
                        print(f"Image uploaded successfully for action_data_id {action_data_id}.")
                    else:
                        print(f"Failed to upload image for action_data_id {action_data_id}. Status code: {response.status_code}")
                        print("Response message:", response.text)

        print("")
        print("---------------------------------------------------------------")
        print("rows: ", len(processed_df))
        print(f"--------------------End Json Payload { date } --------------------")

        return True

    except Exception as e:
        print(f"Error processing action data: {e}")
        return False

if __name__ == "__main__":
    date = "2025-12-03"

    # location = "新莊"
    # location = "新竹"
    location = "西台南"
    # location = "鳳山"
    # location = "中台中"
    # location = "新店"

    process_action_data(date, location)

    # # Load configuration from a JSON file
    # config_path = "config.json"
    
    # with open(config_path, "r") as config_file:
    #     config = json.load(config_file)

    # location_id = config["locations"][location]["LOCATION"]
    
    # folder_path = f"output/{location}/{date}"
    # file_path = f"{folder_path}/{date}_combined_region_table.csv"
    
    # processed_df = process_camera_data(file_path)
    # processed_df["location"] = location_id
    # processed_df['datetime'] = processed_df['datetime'].apply(lambda x: str(x))

    # json_payload = processed_df.to_json(orient="records")

    # # Upload the JSON payload to the server
    # upload(json_payload)

    # print("")
    # print("rows: ", len(processed_df))
    # print(f"--------------------End Json Payload { date } --------------------")
    # processed_df.to_csv(f"{folder_path}/{date}_combined_region_table_filtered.csv", index=False)