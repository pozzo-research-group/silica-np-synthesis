import datetime
import subprocess
import shlex

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


