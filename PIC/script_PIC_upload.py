import os
import pandas as pd

from pathlib import Path

import requests
import ast
import json
import time

def upload(json_payload, url="https://nexretail-camera-station-v2.de.r.appspot.com/data_storage/action_data_upload/"):
    print("uploading action data...")
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json_payload, headers=headers)

    time.sleep(2)

    if response.status_code == 201:
        print("\nData uploaded successfully.")
        print("Response message:", response.json())

        return response.json().get("action_data_id")
    else:
        print(f"\nFailed to upload data. Status code: {response.status_code}")
        print("Response message:", response.json().get("message", "No message in response"))


location = "桃園PIC"
date_stamp = "2025-08-23"
file_directory = ""
base_directory = f"csv/{location}/{date_stamp}/"
folder_path = f"output/{location}/{date_stamp}/"

csv_file = os.path.join(folder_path, f"{date_stamp}_combined.csv")
df = pd.read_csv(csv_file)

if df is not None:
    print("DataFrame loaded successfully.")
    print("Shape:", df.shape)
    print(df.head())
else:
    print("DataFrame not loaded.")


df = df.rename(columns={'baseline': 'solution'})
df = df.rename(columns={'gender': 'combined_gender', 'age': 'combined_age'})

df['img_path'] = df['img_path'].apply(lambda x: ast.literal_eval(x)[0] if pd.notnull(x) else x)
df['actions'] = ''

for idx, row in df.iterrows():
    # if idx == 0:
    row_df = pd.DataFrame([row])
    json_payload = row_df.to_json(orient="records")
    print("")
    print("---------------------")
    print(f"Uploading row {idx + 1}/{len(df)}")
    print(json_payload)
    action_data_id = upload(json_payload)

    this_datetime = pd.to_datetime(row['datetime'])
    formatted_datetime = this_datetime.strftime("%Y-%m-%dT%H_00_00")

    image_upload_url = f"https://nexretail-camera-station-v2.de.r.appspot.com/data_storage/action_data_image_upload/{action_data_id}/"
    with open(f"{base_directory}{formatted_datetime}/{row['img_path']}", 'rb') as img_file:
        files = {'image': (os.path.basename(f"{base_directory}{formatted_datetime}/{row['img_path']}"), img_file, 'image/jpeg')}
        response = requests.post(image_upload_url, files=files)
        
        if response.status_code == 201:
            print(f"Image uploaded successfully for action_data_id {action_data_id}.")
        else:
            print(f"Failed to upload image for action_data_id {action_data_id}. Status code: {response.status_code}")
            print("Response message:", response.text)
    
    video_upload_url = f"https://nexretail-camera-station-v2.de.r.appspot.com/data_storage/action_data_video_upload/{action_data_id}/"
    with open(f"{base_directory}{row['mp4_path']}", 'rb') as video_file:
        files = {'video': (os.path.basename(f"{base_directory}{row['mp4_path']}"), video_file, 'video/mp4')}
        response = requests.post(video_upload_url, files=files)

        if response.status_code == 201:
            print(f"Video uploaded successfully for action_data_id {action_data_id}.")
        else:
            print(f"Failed to upload video for action_data_id {action_data_id}. Status code: {response.status_code}")
            print("Response message:", response.text)