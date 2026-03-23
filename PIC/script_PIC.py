import ast
import os
import pandas as pd
from datetime import datetime, timedelta

import json
from externals.read_yaml import save_gif_from_imglist

AGE_MAP = {
    0: "0-15",
    1: "16-30",
    2: "31-45",
    3: "46-60",
    4: "61-"
}

location = "桃園PIC"
date_stamp = "2025-08-23"
file_directory = ""
base_directory = f"csv/{location}/{date_stamp}/"
folder_path = f"output/{location}/{date_stamp}"

start_time = 9
end_time = 23

cameras = ["cam001", "cam002", "cam003", "cam004"]
solutions = ["cam001_smoking_room1", "cam002_region2", "cam003_smoking_room2", "cam004_region3"]


dfs = []

for hour in range(start_time, end_time + 1):
    hour_str = f"{hour:02d}_00_00"
    base_time_stamp = date_stamp + "T" + hour_str
    current_time = datetime.strptime(base_time_stamp, "%Y-%m-%dT%H_%M_%S").replace(hour=hour)
    file_directory = os.path.join(base_directory, base_time_stamp)
    print("------------------------------------------------")
    print(f"Processing hour: {hour_str}")
    print(f"File directory:", {file_directory})

    for i in range(len(cameras)):
        camera = cameras[i]
        solution = solutions[i]
        file_path = os.path.join(file_directory, f"{camera}/{solution}_{base_time_stamp}.csv")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            dfs.append(df)
            print(f"Loaded {file_path} with shape: {df.shape}")
        else:
            print(f"File not found: {file_path}")

print("------------------------------------------------")
if dfs:
    non_empty_dfs = [df for df in dfs if not df.empty]
    if non_empty_dfs:
        combined_df = pd.concat(non_empty_dfs, ignore_index=True)
        print(f"Combined dataframe shape: {combined_df.shape}")
    else:
        print("All loaded DataFrames are empty for this hour.")
else:
    print("No files to combine for this hour.")

combined_df = combined_df[combined_df['staytime'] >= 12]

print(f"filtered combined dataframe shape: {combined_df.shape}")

combined_df["gif_path"] = ""
combined_df["mp4_path"] = ""
combined_df["action_summary"] = ""
combined_df["table_head_count"] = 1
combined_df["location"] = 7
combined_df["staytime"] = combined_df["staytime"].astype(int).astype(str)
# combined_df["age"] = combined_df["age"].astype(int).astype(str)

combined_df['age'] = combined_df['age'].map(AGE_MAP)

def save_gif_and_get_path(img_list, idx):
    gif_path = save_gif_from_imglist(img_list, base_directory, to_mp4=False)
    
    return gif_path

def save_mp4_and_get_path(img_list, idx):
    mp4_path = save_gif_from_imglist(img_list, base_directory, to_mp4=True)
    
    return mp4_path

for idx, row in combined_df.iterrows():
    # if idx == 0:
    print("---------------------")
    print(f"processing row {idx + 1}/{len(combined_df)}")
    this_datetime = pd.to_datetime(row['datetime'])
    formatted_datetime = this_datetime.strftime("%Y-%m-%dT%H_00_00")

    img_list = row["img_path"]

    if isinstance(img_list, str):
        img_list = ast.literal_eval(img_list)
        img_list = [f"{formatted_datetime}/{img}" for img in img_list]

    # gif_path = save_gif_and_get_path(img_list, combined_df["track_id"])
    mp4_path = save_mp4_and_get_path(img_list, combined_df["track_id"])

    # combined_df.loc[idx, "gif_path"] = gif_path[0]
    # gif_size = os.path.getsize(f"{base_directory}/{gif_path[0]}")
    # print(f"GIF saved: {combined_df.loc[idx, 'gif_path']} ({gif_size / 1024 / 1024:.2f} MB)")

    if not mp4_path:
        print(f"MP4 path is empty for row {idx + 1}, skipping...")
        combined_df.drop(idx, inplace=True)
        continue

    combined_df.loc[idx, "mp4_path"] = mp4_path[0]
    mp4_size = os.path.getsize(f"{base_directory}/{mp4_path[0]}")
    print(f"MP4 saved: {combined_df.loc[idx, 'mp4_path']} ({mp4_size / 1024 / 1024:.2f} MB)")

    if row["baseline"] in ["region2", "region3"]:
        combined_df.loc[idx, "action_summary"] = "banned_smoking"
    else:
        combined_df.loc[idx, "action_summary"] = "smoking"
    print(combined_df.loc[idx, "action_summary"])

    
print("------------------------------------------------")
print("Result DataFrames:")
print(f"shape: {combined_df.shape}")
print(f"columns: {list(combined_df.columns)}")

combined_df.to_csv(f"{folder_path}/{date_stamp}_combined.csv", index=False)
print("------------------------------------------------")
