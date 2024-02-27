import os
import time
import json

# 파일 경로 설정
script_directory = os.path.dirname(os.path.abspath(__name__))
channel_count_file_path = os.path.join(script_directory, 'channel_count.txt')
channels_file_path = os.path.join(script_directory, 'channels.json')
delays_file_path = os.path.join(script_directory, 'delays.json')

# channels 리스트 정의
channels = []

#쿠키 저장 변수
def save_cookie_info(SES, AUT):
    cookie_data = {
        "NID_SES": SES,
        "NID_AUT": AUT
    }
    cookie_file_path = "cookie.json"  # 쿠키 파일 경로 설정
    with open(cookie_file_path, "w") as cookie_file:
        json.dump(cookie_data, cookie_file, indent=2)
    print("쿠키 정보가 성공적으로 저장되었습니다.")

# 채널 수 불러오기
if os.path.exists(channels_file_path):
    with open(channels_file_path, "r") as f:
        channels = json.load(f)
    channel_count = len(channels)
else:
    channel_count = 0

# 기존 딜레이 정보 불러오기
if os.path.exists(delays_file_path):
    with open(delays_file_path, "r") as f:
        delays = json.load(f)
else:
    delays = {}

def 다시입력하기():
        print("다시 입력해주세요.\n")
        time.sleep(1)

while True:
    print("Chzzk 자동녹화 설정")
    print("\n1. 채널 설정\n2. 녹화 설정\n3. 쿠키 설정(성인 인증 관련)\n4. 나가기")
    값 = str(input("실행하고 싶은 번호를 입력해주세요: "))
    if 값 == "1":
        while True:
            print("\n1. 채널 추가\n2. 채널 삭제\n3. 채널 on/off\n4. 돌아가기")
            값1 = str(input("실행하고 싶은 번호를 입력해주세요: "))
            if 값1 == "1":
                id = str(input("원하시는 스트리머 채널의 고유 id를 적어주세요: "))
                name = str(input("스트리머 이름을 적어주세요:  "))
                output_dir = str(input("저장 경로를 지정해주세요(이름만 적으면 프로그램과 같은 위치에 저장 됩니다): "))
                while True:
                    answer = str(input(f"id: {id}, 이름: {name}, 저장 경로: {output_dir} 가 맞나요? (Y/N): "))
                    if answer == "Y":
                        channel_count += 1
                        identifier = f"ch{channel_count}"
                        channels.append({
                            "id": id,
                            "name": name,
                            "output_dir": output_dir,
                            "identifier": identifier,
                            "active": "on"
                        })
                        delays[identifier] = channel_count - 1
                        
                        # 파일에 데이터 추가
                        with open(channels_file_path, "w") as f:
                            json.dump(channels, f, indent=2)
                            f.write('\n')  # 각 채널을 개별 줄로 저장하기 위해 개행 문자 추가
                        print("channels.json 파일이 수정되었습니다.")
                        with open(delays_file_path, "w") as f:
                            json.dump(delays, f, indent=2)
                        print("delays.json 파일이 수정되었습니다.")
                        with open(channel_count_file_path, "w") as f:
                            f.write(str(channel_count))
                        break
                    elif answer == "N":
                        print("그러면 다시 입력해 주세요")
                        time.sleep(1)
                        break
                    else:
                        print("다시 입력해주세요.\n")
                        time.sleep(1)
                        
            elif 값1 == "2":
                # 채널 삭제
                print("현재 설정된 채널 목록:")
                for 채널 in channels:
                    print(f"id: {채널['id']}, 이름: {채널['name']}")

                삭제할_채널_ID = input("삭제할 채널의 ID를 입력하세요: ")
                삭제할_채널_인덱스 = -1
                for index, 채널 in enumerate(channels):
                    if 채널['id'] == 삭제할_채널_ID:
                        삭제할_채널_인덱스 = index
                        break
                if 삭제할_채널_인덱스 != -1:
                    del_채널 = channels.pop(삭제할_채널_인덱스)
                    print(f"삭제된 채널: id: {del_채널['id']}, 이름: {del_채널['name']}")
                    # 파일에 데이터 추가
                    with open(channels_file_path, "w") as f:
                        json.dump(channels, f, indent=2)
                        f.write('\n')  # 각 채널을 개별 줄로 저장하기 위해 개행 문자 추가
                    print("channels.json 파일이 수정되었습니다.")
                    # channel_count 수정
                    channel_count -= 1
                    with open(channel_count_file_path, "w") as f:
                        f.write(str(channel_count))
                    # delays 수정
                    delays.pop(삭제할_채널_ID, None)  # 삭제된 채널 ID에 해당하는 딕셔너리 항목 제거
                    for idx, 채널 in enumerate(channels):
                        채널['identifier'] = f'ch{idx + 1}'  # 채널 번호 다시 정렬
                    with open(delays_file_path, "w") as f:
                        delays_data = {f'ch{i+1}': i for i in range(len(channels))}
                        json.dump(delays_data, f, indent=2)
                    print("delays.json 파일이 수정되었습니다.")
                    # 채널 삭제 후에도 identifier 변경을 channels.json에 적용
                    with open(channels_file_path, "w") as f:
                        json.dump(channels, f, indent=2)
                        f.write('\n')  # 각 채널을 개별 줄로 저장하기 위해 개행 문자 추가
                    print("channels.json 파일이 재수정되었습니다.")
                else:
                    print(f"{삭제할_채널_ID} ID를 가진 채널이 존재하지 않습니다.")

            elif 값1 == "3":
                print("현재 채널 리스트:")
                for 채널 in channels:
                    print(f"id: {채널['id']}, 이름: {채널['name']}, 녹화 상태: {'On' if 채널.get('active', True) == 'on' else 'Off'}")

                채널_ID = input("채널 ID의 녹화 상태를 변경합니다:  ")
                for 채널 in channels:
                    if 채널['id'] == 채널_ID:
                        현재_상태 = 채널.get('active', 'on')
                        채널['active'] = 'off' if 현재_상태 == 'on' else 'on'
                        print(f"{채널['name']} 채널의 녹화 상태가 {'꺼짐' if 현재_상태 == 'on' else '켜짐'}로 변경되었습니다.")
                        # 파일에 데이터 추가
                        with open(channels_file_path, "w") as f:
                            json.dump(channels, f, indent=2)
                            f.write('\n')  # 각 채널을 개별 줄로 저장하기 위해 개행 문자 추가
                        print("channels.json 파일이 수정되었습니다.")
                        break
                else:
                    print(f"ID가 {채널_ID}인 채널을 찾을 수 없습니다.")
            
            elif 값1 == "4":
                print("메뉴로 돌아갑니다")
                time.sleep(1)
                break
                
            else:
                print("다시 입력해주세요./이전 메뉴로 돌아갑니다.\n")
                time.sleep(1)

    elif 값 == "2":
        while True:
            print("\n1. 녹화용 쓰레드 수 설정\n2. 방송 재탐색 주기\n3. 녹화파일 해상도\n4. 돌아가기")
            값2 = str(input("실행하고 싶은 번호를 입력해주세요: "))
        
            if 값2 == "1":
                쓰레드_파일_경로 = os.path.join(script_directory, 'thread.txt')
                with open(쓰레드_파일_경로, "r") as thread_file:
                    쓰레드 = thread_file.readline().strip()
                print(f"현재 녹화용 쓰레드 수는 {쓰레드}입니다.")
                print("2~4쓰레드 권장, 저사양은 2쓰레드 / 여유있으면 4쓰레드")
                새_쓰레드 = str(input("변경할 쓰레드 수를 입력하세요: "))
                # TODO: 입력된 값을 쓰레드 변수에 적용
                with open(쓰레드_파일_경로, "w") as thread_file:
                    thread_file.write(새_쓰레드)
                print("쓰레드 수가 변경되었습니다.")
        
            elif 값2 == "2":
                재탐색_주기_파일_경로 = os.path.join(script_directory, 'time_sleep.txt')
                with open(재탐색_주기_파일_경로, "r") as time_sleep_file:
                    재탐색_주기 = time_sleep_file.readline().strip()
                print(f"현재 방송 재탐색 주기는 {재탐색_주기}초 입니다.")
                새_재탐색_주기 = str(input("변경할 재탐색 주기를 입력하세요 (초 단위): "))
                with open(재탐색_주기_파일_경로, "w") as time_sleep_file:
                    time_sleep_file.write(새_재탐색_주기)
                print("방송 재탐색 주기가 변경되었습니다.")
        
            elif 값2 == "3":
                해상도_파일_경로 = os.path.join(script_directory, 'resolution.txt')
                with open(해상도_파일_경로, "r") as resolution_file:
                    해상도 = resolution_file.readline().strip()
                print(f"현재 녹화파일 해상도는 {해상도}입니다.")
                새_해상도 = str(input("변경할 해상도를 입력하세요 (예: best, 720p, 1080p): "))
                # TODO: 입력된 값을 해상도 변수에 적용
                with open(해상도_파일_경로, "w") as resolution_file:
                    resolution_file.write(새_해상도)
                print("녹화파일 해상도가 변경되었습니다.")
        
            elif 값2 == "4":
                print("메뉴로 돌아갑니다")
                time.sleep(1)
                break
            
            else:
                print("다시 입력해주세요./이전 메뉴로 돌아갑니다.\n")
                time.sleep(1)
        
        else:
            print("다시 입력해주세요./이전 메뉴로 돌아갑니다.\n")
            time.sleep(1)
                
            
    elif 값 == "3":
        SES = str(input("SES를 입력하세요: "))
        AUT = str(input("AUT를 입력하세요: "))
        save_cookie_info(SES, AUT)
        
    elif 값 == "4":
        print("설정을 마칩니다.")
        break
    else:
        print("다시 입력해주세요.\n")
        time.sleep(1)
