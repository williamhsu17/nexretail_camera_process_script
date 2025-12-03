from datetime import datetime, timedelta
import json
import os
import pandas as pd
import requests

OUTPUT_SET = ["entrance", "region_car", "region_table"]

SOLUTION = {
    1: "entrance_shop",
    2: "Negotiation_table_1",
    3: "Negotiation_table_2",
    4: "YARIS_CROSS",
    5: "bZ4x",
    6: "Negotiation_table_None",
    7: "RAV4",
    8: "Negotiation_table_4",
    9: "Negotiation_table_5",
    10: "Negotiation_table_6",
    11: "VIOS",
    12: "car_None",
    13: "COROLLA_SPORT",
    14: "Negotiation_table_7",
    15: "Negotiation_table_8",
    16: "Negotiation_table_9",
    17: "SIENTA",
    18: "ALTIS",
    19: "Negotiation_table_10",
    20: "Negotiation_table_11",
    21: "SIENTA",
    22: "entrance_shop2",
    23: "Negotiation_table_3",
    24: "car_white",
    25: "VIOS2",
    26: "SIENTA2",
    27: "SIENTA3",
    28: "COROLLA_CROSS",
    29: "ALTIS2",
    30: "smoking_room1",
    31: "region2",
    32: "smoking_room2",
    33: "region3",
}

GENDER_MAP = {
    0: "Male",
    1: "Female"
}
AGE_MAP = {
    0: "0-15",
    1: "16-30",
    2: "31-45",
    3: "46-60",
    4: "61-"
}

class CameraDataProcessor:
    def __init__(self, camera, location_id, entrance, region_car, region_table, base_directory, base_day_stamp, processor_type="default", start_time = 9, end_time = 20, output_base_direction = "output"):
        self.camera = camera
        self.location_id = location_id
        self.entrance = entrance
        self.region_car = region_car
        self.region_table = region_table

        self.solution_sets = {
            "entrance": self.entrance,
            "region_car": self.region_car,
            "region_table": self.region_table
        }
        
        self.base_directory = base_directory
        self.file_directory = ""

        self.base_day_stamp = base_day_stamp
        self.base_time_stamp = ""
        self.current_time = ""

        self.output = False

        self.processor_type = processor_type
        
        self.start_time = start_time
        self.end_time = end_time 
        
        self.df = {key: pd.DataFrame() for key in ["base_text"] + OUTPUT_SET}
        self.df_output = {key: pd.DataFrame() for key in ["base_text"] + OUTPUT_SET}

        self.df_object = pd.DataFrame()
        self.df_object_output = pd.DataFrame()

        self.df_object_reference = pd.DataFrame()
        self.df_object_reference_output = pd.DataFrame()

        self.inference_gap = []

        self.log = []
        
        self.output_directory = os.path.join(output_base_direction, self.base_day_stamp)
        os.makedirs(self.output_directory, exist_ok=True)

        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)
            print(f"Directory {self.output_directory} created.")
        
        print("Processing output for NexRetail camera data")
        print(f"at { self.base_directory }")
    
    def process_output_base_text(self):
        """
        process output task for base_text processor type
        """
        if not self.df["base_text"].empty:
            # 將之前的資料修正preid
            if self.output:
                output_time = self.current_time - timedelta(hours=1)
                output_hour = output_time.hour

                hour_str = f"{output_hour:02d}_00_00"
                base_time_stamp = self.base_day_stamp + "T" + hour_str
                file_directory = os.path.join(self.base_directory, base_time_stamp)
            else:
                file_directory = self.file_directory

            json_path = os.path.join(file_directory, f"system.json")

            with open(json_path) as f:
                for line in f:
                    data = json.loads(line)
            
            system_json = data

            if system_json.get('remap_reid', False): # 確認系統檔中reid的資訊
                self.df["base_text"]['raw_id'] = self.df["base_text"]['id'] # 先將track_id 存起來
                self.df["base_text"]['id'] = self.df["base_text"]['id'].astype(str) # 從json讀來的檔中key會變字串，因此先轉字串
                # 如果 remap表中有該track_id，就重新remap id(pre_id), 沒有則保持元id
                self.df["base_text"]['id'] = self.df["base_text"]['id'].apply(lambda x: system_json['remap_reid'].get(x, {"pre_id": x})["pre_id"])
                self.df["base_text"]['id'] = self.df["base_text"]['id'].astype(int)# 轉回int
            else:
                print("\nprocessing preid error\n")

            self.df_object = self.df["base_text"]

            self.df_object_reference = self.df["base_text"].groupby('id').agg({
                'age': lambda x: x.mode().iloc[0] if not x.mode().empty else None,
                'gender': lambda x: x.mode().iloc[0] if not x.mode().empty else None,
            }).reset_index()

            self.df_object_reference['gender'] = self.df_object_reference['gender'].map(GENDER_MAP)
            self.df_object_reference['age'] = self.df_object_reference['age'].map(AGE_MAP)

            # 將修正preid的資料加入主表
            self.df_output["base_text"] = pd.concat([self.df_output["base_text"], self.df["base_text"]], ignore_index=True).sort_values(by=['datetime']).reset_index(drop=True)
            self.df_object_output = pd.concat([self.df_object_output, self.df_object], ignore_index=True)
            self.df_object_reference_output = pd.concat([self.df_object_reference_output, self.df_object_reference], ignore_index=True)

            print("Total row number of df_output:", self.df_output["base_text"].shape[0])

            self.df["base_text"] = pd.DataFrame()
            
            return True
        else:
            return False
    
    def process_output_entrance(self):
        """
        process output task for entrance processor type
        """
        if not self.df["entrance"].empty:
            print("Total row number of df_output(entrance) before cleaning:", self.df["entrance"].shape[0])

            self.df["entrance"]['age'] = self.df["entrance"]['track_id'].map(self.df_object_reference.set_index('id')['age'])
            self.df["entrance"]['gender'] = self.df["entrance"]['track_id'].map(self.df_object_reference.set_index('id')['gender'])

            # calculate staytime
            self.df_object = self.df_object[self.df_object['id'].isin(self.df["entrance"]['track_id'])]

            self.df_object['datetime'] = pd.to_datetime(self.df_object['datetime'])
            self.df_object['hour'] = self.df_object['datetime'].dt.floor('h')
            self.df_object = self.df_object.groupby(['id', 'hour']).filter(lambda x: len(x) >= 20)
            # self.df_object['h_mark'] = self.df_object.groupby(['id', 'hour'])['id'].transform('size').apply(lambda x: 'Y' if x < 20 else 'N')

            self.df["entrance"]['staytime'] = ''

            end_of_day = datetime.strptime(self.base_day_stamp, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            rows_to_remove = []

            for track_id, group in self.df["entrance"].groupby('track_id'):
                for _, row in group.iterrows():
                    start_time = row['datetime']
                    next_index = group.index.get_loc(row.name) + 1
                    if next_index < len(group):
                        end_time = group.iloc[next_index]['datetime']
                    else:
                        end_time = end_of_day

                    filtered_df = self.df_object[(self.df_object['id'] == track_id) & 
                                                 (self.df_object['datetime'] >= start_time) & 
                                                 (self.df_object['datetime'] <= end_time)]
                    
                    max_datetime = filtered_df['datetime'].max() if not filtered_df.empty else None
                    min_datetime = filtered_df['datetime'].min() if not filtered_df.empty else None

                    if max_datetime and min_datetime:
                        time_difference = max_datetime - min_datetime
                        
                        if time_difference < timedelta(minutes=5):
                            rows_to_remove.append(row.name)
                            # self.df.at[row.name, 'is_remove'] = 'Y'
                            continue

                        hours = time_difference.seconds // 3600
                        minutes = (time_difference.seconds % 3600) // 60
                        seconds = time_difference.seconds % 60
                        formatted_time_difference = f"{hours:02}:{minutes:02}:{seconds:02}"

                        self.df["entrance"].at[row.name, 'staytime'] = formatted_time_difference

            self.df["entrance"].drop(index=rows_to_remove, inplace=True)
            self.df["entrance"] = self.df["entrance"][self.df["entrance"]['staytime'] != ""]

            self.df["entrance"]['second_show'] = ''
            mask = (self.df["entrance"].groupby('track_id')['track_id'].transform('size') > 1) & (self.df["entrance"].groupby('track_id').cumcount() != 0)
            self.df["entrance"].loc[mask, 'second_show'] = 'Y'

            self.df["entrance"]['group_head_count'] = self.df["entrance"].groupby('group')['group'].transform('size')
            self.df["entrance"]['group_gender'] = self.df["entrance"].groupby('group')['gender'].transform(lambda x: "")
            self.df["entrance"]['group_with_youth'] = self.df["entrance"].groupby('group')['age'].transform(lambda x: 'Y' if '0-15' in x.values else 'N')
            self.df["entrance"]['is_group'] = self.df["entrance"].groupby('group').cumcount().apply(
                lambda x: 'Y' if x == 0 else ''
            )
            self.df["entrance"]['is_group'] = ''
            self.df["entrance"].loc[self.df["entrance"].groupby('group').head(1).index, 'is_group'] = \
                self.df["entrance"].groupby('group')['group'].transform('size').gt(1).map({True: 'Y', False: ''})
            
            df_filtered = self.df["region_table"][self.df["region_table"]["staytime"] >= 500]

            result_df = (
                df_filtered.groupby(['track_id', 'solution'])
                .agg(min_datetime=('datetime', 'min'), max_datetime=('datetime', 'max'))
                .reset_index()
            )

            solutions_by_track_id = (
                result_df.groupby('track_id')['solution']
                .apply(', '.join)
                .reset_index()
                .rename(columns={'solution': 'region'})
            )

            self.df["entrance"] = self.df["entrance"].merge(solutions_by_track_id, on='track_id', how='left')

            # self.df["entrance"]['region'] = ""

            self.df["entrance"]["M0-15"] = self.df["entrance"].apply(lambda row: 1 if row["age"] == "0-15" and row["gender"] == "Male" else 0, axis=1)
            self.df["entrance"]["M16-30"] = self.df["entrance"].apply(lambda row: 1 if row["age"] == "16-30" and row["gender"] == "Male" else 0, axis=1)
            self.df["entrance"]["M31-45"] = self.df["entrance"].apply(lambda row: 1 if row["age"] == "31-45" and row["gender"] == "Male" else 0, axis=1)
            self.df["entrance"]["M46-60"] = self.df["entrance"].apply(lambda row: 1 if row["age"] == "46-60" and row["gender"] == "Male" else 0, axis=1)
            self.df["entrance"]["F0-15"] = self.df["entrance"].apply(lambda row: 1 if row["age"] == "0-15" and row["gender"] == "Female" else 0, axis=1)
            self.df["entrance"]["F16-30"] = self.df["entrance"].apply(lambda row: 1 if row["age"] == "16-30" and row["gender"] == "Female" else 0, axis=1)
            self.df["entrance"]["F31-45"] = self.df["entrance"].apply(lambda row: 1 if row["age"] == "31-45" and row["gender"] == "Female" else 0, axis=1)
            self.df["entrance"]["F46-60"] = self.df["entrance"].apply(lambda row: 1 if row["age"] == "46-60" and row["gender"] == "Female" else 0, axis=1)

            self.df["entrance"]["Total Male + Female"] = self.df["entrance"]["M0-15"] + self.df["entrance"]["M16-30"] + self.df["entrance"]["M31-45"] + self.df["entrance"]["M46-60"] + self.df["entrance"]["F0-15"] + self.df["entrance"]["F16-30"] + self.df["entrance"]["F31-45"] + self.df["entrance"]["F46-60"]
            self.df["entrance"]["Total Male"] = self.df["entrance"]["M0-15"] + self.df["entrance"]["M16-30"] + self.df["entrance"]["M31-45"] + self.df["entrance"]["M46-60"]
            self.df["entrance"]["Total Female"] =self.df["entrance"]["F0-15"] + self.df["entrance"]["F16-30"] + self.df["entrance"]["F31-45"] + self.df["entrance"]["F46-60"]

            self.df["entrance"]['location'] = self.location_id

            column_order = ['track_id', 'second_show', 'gender', 'age', 'staytime', 'solution', 'direction', 'region', 'group', 'is_group', 'group_head_count', 'group_gender', 'group_with_youth', 'datetime', 'Camera', 'Shop', 'M0-15', 'M16-30', 'M31-45', 'M46-60', 'F0-15', 'F16-30', 'F31-45', 'F46-60', 'Total Male + Female', 'Total Male', 'Total Female', 'location']
            self.df["entrance"] = self.df["entrance"][column_order]

            self.df_output["entrance"] = pd.concat([self.df_output["entrance"], self.df["entrance"]], ignore_index=True).sort_values(by=['datetime']).reset_index(drop=True)

            print("Total row number of df_output(entrance):", self.df_output["entrance"].shape[0])
        
            return True
        else:
            return False

    def process_output(self):
        """
        process output task for general processor type
        """
        if not self.df[self.processor_type].empty:
            print(f"process age and gender for { self.processor_type }")
            self.df[self.processor_type]['age'] = self.df[self.processor_type]['track_id'].map(self.df_object_reference.set_index('id')['age'])
            self.df[self.processor_type]['gender'] = self.df[self.processor_type]['track_id'].map(self.df_object_reference.set_index('id')['gender'])
            
            self.df_output[self.processor_type] = pd.concat([self.df_output[self.processor_type], self.df[self.processor_type]], ignore_index=True).sort_values(by=['datetime']).reset_index(drop=True)
            
            column_order = ['track_id', 'gender', 'age', 'solution', 'actions', 'img_path', 'staytime', 'datetime', 'Camera', 'Shop']

            self.df_output[self.processor_type] = self.df_output[self.processor_type][column_order]
            
            print(f"Total row number of df_output({ self.processor_type }): {self.df_output[self.processor_type].shape[0]}")

            return True

        else:
            return False

    def process_save_base_text(self):
        """
        process saving task for base_text processor type
        """
        output_file_path = os.path.join(self.output_directory, f"{self.base_day_stamp}_combined_{self.processor_type}_object_reference.csv")
        self.df_object_reference_output.to_csv(output_file_path, index=False)
        print("Total row number of df_object_reference:", self.df_object_reference.shape[0])
        print(f"Combined df_object_reference saved to: {output_file_path}")

        output_file_path = os.path.join(self.output_directory, f"{self.base_day_stamp}_combined_{self.processor_type}.csv")
        self.df_output[self.processor_type].to_csv(output_file_path, index=False)
        print(f"Combined df saved to: {output_file_path}")
    
    def process_save(self):
        """
        process saving task for general processor type
        """
        output_file_path = os.path.join(self.output_directory, f"{self.base_day_stamp}_combined_{self.processor_type}.csv")

        self.df_output[self.processor_type].to_csv(output_file_path, index=False)
        print(f"Combined df({ self.processor_type }) saved to: {output_file_path}")

        if (self.processor_type == "entrance"):
            print(f"--------------------Json Payload { self.base_day_stamp } --------------------")
            print("")
            self.df_output["entrance"].rename(columns={"Camera": "camera"}, inplace=True)
            self.df_output["entrance"].rename(columns={"Shop": "shop"}, inplace=True)
            self.df_output["entrance"].rename(columns={"M0-15": "m_0_15"}, inplace=True)
            self.df_output["entrance"].rename(columns={"M16-30": "m_16_30"}, inplace=True)
            self.df_output["entrance"].rename(columns={"M31-45": "m_31_45"}, inplace=True)
            self.df_output["entrance"].rename(columns={"M46-60": "m_46_60"}, inplace=True)
            self.df_output["entrance"].rename(columns={"F0-15": "f_0_15"}, inplace=True)
            self.df_output["entrance"].rename(columns={"F16-30": "f_16_30"}, inplace=True)
            self.df_output["entrance"].rename(columns={"F31-45": "f_31_45"}, inplace=True)
            self.df_output["entrance"].rename(columns={"F46-60": "f_46_60"}, inplace=True)
            self.df_output["entrance"].rename(columns={"Total Male + Female": "total_male_female"}, inplace=True)
            self.df_output["entrance"].rename(columns={"Total Male": "total_male"}, inplace=True)
            self.df_output["entrance"].rename(columns={"Total Female": "total_female"}, inplace=True)
            json_payload = self.df_output["entrance"].to_json(orient="records")
            print(json_payload)

            # Upload the JSON payload to the server
            url = "https://nexretail-camera-station-v2.de.r.appspot.com/data_storage/upload/"
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, data=json_payload, headers=headers)

            if response.status_code == 201:
                print("\nData uploaded successfully.")
                print("Response message:", response.json().get("message", "No message in response"))
            else:
                print(f"\nFailed to upload data. Status code: {response.status_code}")
                print("Response message:", response.json().get("message", "No message in response"))
            
            print("")
            print(f"--------------------End Json Payload { self.base_day_stamp } --------------------")


    def process_hourly_base_text(self):
        hourly_cam_id_list = []
        df_cameras_list = []
        df_cameras = pd.DataFrame()
        
        for camera in self.camera:
            base_txt_path = os.path.join(self.file_directory, f"{camera}.txt")

            try:
                df_camera_base_text = pd.read_csv(base_txt_path, sep='\s+')

                first_row = df_camera_base_text.iloc[0].to_dict() if not df_camera_base_text.empty else None

                # Sort the DataFrame by 'id' and 'frame_idx'
                df_camera_base_text = df_camera_base_text.sort_values(by=['id', 'frame_idx']).reset_index(drop=True)
                # Add a 'camera' field to record the camera
                df_camera_base_text.insert(df_camera_base_text.columns.get_loc('id'), 'camera', camera)

                # Append the DataFrame to the list
                df_cameras_list.append(df_camera_base_text)
                
                hourly_cam_id_list.append(first_row['id'])

            except Exception as e:
                print(f"Error reading file {base_txt_path}: {e}")
        
        if 1 in hourly_cam_id_list:
            print("Inference gap detected")
            self.output = True
            self.processor_output(processor_type="base_text")
            for processor_type in OUTPUT_SET:
                self.processor_output(processor_type=processor_type)
            for processor_type in OUTPUT_SET:
                self.df[processor_type] = pd.DataFrame()
            print("")
        else:
            self.output = False
        
        # 計算這輪的camera資料 --------------------------------
        # print(df_cameras_list)
        df_cameras = pd.concat(df_cameras_list, ignore_index=True)
        df_cameras['datetime'] = df_cameras['frame_idx'].apply(
            lambda frame_idx: self.current_time + timedelta(seconds=frame_idx / 10)
        )
        self.df["base_text"] = pd.concat([self.df["base_text"], df_cameras], ignore_index=True).sort_values(by=['datetime']).reset_index(drop=True)
        print("Total rwo number of df_cameras:", df_cameras.shape[0])
        print("Total rwo number of df:", self.df["base_text"].shape[0])

    def process_hourly_entrance(self):
        """
        process hourly task for entrance data
        """
        df_list = []
        dfs = pd.DataFrame()
        
        for camera in self.camera:
            # camera_number = int(camera[3:])
            # modified_camera = f"cam_{camera_number}"

            for solution_id in self.solution_sets["entrance"]:
                solution_name = SOLUTION[solution_id]
                csv_filename = f"{camera}_{solution_name}_{self.base_time_stamp}.csv"
                csv_path = os.path.join(self.file_directory, camera, csv_filename)

                # Check if the file exists before attempting to read it
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    
                    df_list.append(df)
        
        dfs = pd.concat(df_list, ignore_index=True).sort_values(by=['track_id', 'baseline']).reset_index(drop=True)
        dfs['group'] = str(self.current_time) + '_' + dfs['group'].astype(str)

        if 'baseline' in dfs.columns:
            dfs = dfs.rename(columns={'baseline': 'solution'})

        self.df["entrance"] = pd.concat([self.df["entrance"], dfs], ignore_index=True).sort_values(by=['datetime']).reset_index(drop=True)
        
        print(f"Total rwo number of dfs(entrance): { dfs.shape[0] }")
        print(f"Total rwo number of df(entrance): { self.df['entrance'].shape[0] }")

    def process_hourly(self):
        """
        process hourly task for camera data
        """
        df_list = []
        dfs = pd.DataFrame()
        
        for camera in self.camera:
            # camera_number = int(camera[3:])
            # modified_camera = f"cam_{camera_number}"

            for solution_id in self.solution_sets[self.processor_type]:
                solution_name = SOLUTION[solution_id]
                csv_filename = f"{camera}_{solution_name}_{self.base_time_stamp}.csv"
                csv_path = os.path.join(self.file_directory, camera, csv_filename)

                # Check if the file exists before attempting to read it
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    
                    if not df.empty:
                        df_list.append(df)
                    else:
                        # If df is empty, keep its columns by appending an empty DataFrame with the same columns
                        df_list.append(pd.DataFrame(columns=df.columns))

        if df_list:
            dfs = pd.concat(df_list, ignore_index=True).sort_values(by=['track_id', 'baseline']).reset_index(drop=True)

            if 'baseline' in dfs.columns:
                dfs = dfs.rename(columns={'baseline': 'solution'})
        
            self.df[self.processor_type] = pd.concat([self.df[self.processor_type], dfs], ignore_index=True).sort_values(by=['datetime']).reset_index(drop=True)
            
            print(f"Total rwo number of dfs({ self.processor_type }): { dfs.shape[0] }")
            print(f"Total rwo number of df({ self.processor_type }): { self.df[self.processor_type].shape[0] }")
        else:
            print(f"No data found for { self.processor_type }")
        
    def processor_output(self, processor_type=""):
        """
        process output task for sepcific processor type
        """
        if processor_type:
            self.processor_type = processor_type
        print(f"* processor output for {self.processor_type}")    
        if self.processor_type == "base_text":
            self.process_output_base_text()
        elif self.processor_type == "entrance":
            self.process_output_entrance()
        else:
            self.process_output()
        
        return True

    def processor_save(self, processor_type=""):
        """
        process save task for sepcific processor type
        """
        if processor_type:
            self.processor_type = processor_type
        print(f"* processor save for {self.processor_type}")
        if self.processor_type == "base_text":
            self.process_save_base_text()
        else:
            self.process_save()
        
        return True
    
    def processor_hourly(self, processor_type=""):
        """
        process hourly task for sepcific processor type
        """
        if processor_type:
            self.processor_type = processor_type
        if self.processor_type == "base_text":
            self.process_hourly_base_text()
        elif self.processor_type == "entrance":
            self.process_hourly_entrance()
        else:
            self.process_hourly()
        
        return True
    
    def daily_process(self):
        """
        process daily task for camera data
        """
        for hour in range(self.start_time, self.end_time + 1):
            hour_str = f"{hour:02d}_00_00"
            self.base_time_stamp = self.base_day_stamp + "T" + hour_str
            self.current_time = datetime.strptime(self.base_day_stamp, "%Y-%m-%d").replace(hour=hour)
            self.file_directory = os.path.join(self.base_directory, self.base_time_stamp)
            print("------------------------------------------------")
            print(f"Processing hour: {hour_str}")

            if os.path.isdir(self.file_directory):
                self.processor_hourly(processor_type="base_text")
                
                for processor_type in OUTPUT_SET:
                    self.processor_hourly(processor_type=processor_type)

                # update inference gap if track_id has been reset(trigger output)
                if self.output:
                    self.inference_gap.append(hour_str)

                if hour == self.end_time:
                    print("------------------------------------------------")
                    print("DayEnd")
                    self.processor_output(processor_type="base_text")
                    for processor_type in OUTPUT_SET:
                        self.processor_output(processor_type=processor_type)
                    print("------------------------------------------------")

        self.processor_save(processor_type="base_text")
        for processor_type in OUTPUT_SET:
            self.processor_save(processor_type=processor_type)

        return True

    def output_process(self):
        """
        create all output files for camera data
        """
        # processing base_text and create reference
        self.daily_process()

        print("run information")
        print(f"inference_gap: {self.inference_gap}")
        print("\n------------------------------------------------")
