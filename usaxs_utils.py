import datetime
import subprocess
import shlex
import requests

ip = '18.216.44.137'
remote_username = 'ubuntu'
pem_path = '/Users/bgpelkie/silica-np-opt-key.pem'
date_format = "%Y-%m-%d %H:%M:%S"


local_working_directory = './usaxs_queue'
remote_filepath = '~/usaxs_queue/'
data_package_filename = 'packet.txt'


def trigger_usaxs_measurement(sample_name, sample_uuid, sample_composition):

    trigger_data = [datetime.datetime.now().strftime(date_format), sample_name, sample_composition, str(sample_uuid)]
    print('trigger data: ', trigger_data)

    with open(f'{local_working_directory}/{data_package_filename}', 'wt') as f:
        for entry in trigger_data:
            f.write(entry + '\n')

    copy_remote_file(ip, remote_username, remote_filepath, f'{local_working_directory}/{data_package_filename}', pem_path, copy_from=False)


def copy_remote_file(instance_ip, user_name, remote_path, local_path, pem_path,copy_from=True):
    """
    Copies a remote file to the local machine using scp.

    Args:
        instance_ip (str): The public IP address or public DNS of the EC2 instance.
        user_name (str): The username for connecting to the EC2 instance (e.g., 'ec2-user' or 'ubuntu').
        remote_path (str): The full path to the file on the EC2 instance.
        local_path (str): The full path where the file should be saved locally.
        pem_path (str): The path to the .pem file used for SSH authentication.
    """
    # print(instance_ip)
    # print(user_name)
    # print(remote_path)
    # print(local_path)
    # print(pem_path)
    try:
        command = [
            "scp",
            "-i",
            str(pem_path),
        ]
        if copy_from:
            command.extend([
                f"{user_name}@{instance_ip}:{remote_path}",
                str(local_path),
            ])
        else:
            command.extend([
                str(local_path),
                f"{user_name}@{instance_ip}:{remote_path}",
            ])
        
        subprocess.run(shlex.split(' '.join(command)), check=True, capture_output=True)
        print(f"File copied successfully from {remote_path} to {local_path}")
    
    except subprocess.CalledProcessError as e:
         print(f"Error copying file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")



def watch_usaxs_measurement(sample_uuid, ip):

    """
    Starts a monitoring thread to watch USAXS measurements for a given sample UUID.

    Args:
        sample_uuid (str): UUID of the sample being measured
    """
    import threading

    monitor_thread = threading.Thread(target=saxs_monitor, args=(sample_uuid, ip))
    monitor_thread.daemon = True  # Thread will exit when main program exits
    monitor_thread.start()

    return monitor_thread


def saxs_monitor(sample_uuid, usaxs_server_ip, afl_ip):


    usaxs_server_url = 'http://' + usaxs_server_ip + ':5000/check_usaxs_status'
    afl_url = 'http://' + afl_ip + ':5000'

    username = 'test'
    password = 'domo_arigato'



    while True:
        response = requests.post(usaxs_server_url, json={'id': sample_uuid})

        status = response.json()['usaxs_status']

        if status == 'complete':
            break

    # call AFL rinse

    # login
    r = requests.post(
            afl_url + "/login",
            json={"username": username, "password": password},
        )

    token = r.json()["token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    task = {"task_name": "rinseCell"}

    r = requests.post(afl_url + "/enqueue", headers=auth_header, json=task)

    if r.status_code != 200:
            raise Exception(f"Error enqueuing task: {r.json()}")

    return









