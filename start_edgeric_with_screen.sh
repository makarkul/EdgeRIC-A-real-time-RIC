#!/bin/bash

# Check if network and name parameters are provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <network> <container_name>"
    echo "Example: $0 bridge test"
    exit 1
fi

echo "Starting EdgeRIC container with network: $1, name: edgeric_$2"

#export DISPLAY=:93
xhost +local:docker

systemctl stop firewalld

sysctl -w net.ipv4.ip_forward=1

# Start container and setup screen session
docker run -it --rm --network=$1 --name edgeric_$2 --privileged=true \
    -e DISPLAY=$DISPLAY \
    --env=NVIDIA_DRIVER_CAPABILITiES=all \
    --env=NVIDIA-VISIBLE_DEVICES=all \
    --env=QT_X11_NO_MITSHM=1 \
    -v $(pwd):/home/EdgeRIC-A-real-time-RIC:rw \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v /dev:/dev \
    nlpurnhyun/edgeric_base_oaic \
    bash -c "
        cd /home/EdgeRIC-A-real-time-RIC && 
        echo 'Installing screen utility...' &&
        apt update -y && apt install -y screen &&
        echo 'Setting up screen session with 10 windows...' &&
        screen -dmS edgeric -s /bin/bash &&
        sleep 1 &&
        screen -S edgeric -X screen -t 'GNU-Radio' &&
        screen -S edgeric -p 'GNU-Radio' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC\n' &&
        screen -S edgeric -p 'GNU-Radio' -X stuff 'python3 top_block_2ue_no_gui.py\n' &&
        screen -S edgeric -X screen -t 'EPC' &&
        screen -S edgeric -p 'EPC' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC\n' &&
        screen -S edgeric -p 'EPC' -X stuff './run_epc.sh\n' &&
        screen -S edgeric -X screen -t 'ENB' &&
        screen -S edgeric -p 'ENB' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC\n' &&
        screen -S edgeric -p 'ENB' -X stuff './run_enb.sh\n' &&
        screen -S edgeric -X screen -t 'UE' &&
        screen -S edgeric -p 'UE' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC\n' &&
        screen -S edgeric -p 'UE' -X stuff 'ip netns add ue1\n' &&
        screen -S edgeric -p 'UE' -X stuff 'ip netns add ue2\n' &&
        screen -S edgeric -p 'UE' -X stuff './run_srsran_2ue.sh\n' &&
        echo 'Initial screen sessions started:' &&
        echo '  Window 0: GNU-Radio (python3 top_block_2ue_no_gui.py)' &&
        echo '  Window 1: EPC (./run_epc.sh)' &&
        echo '  Window 2: ENB (./run_enb.sh)' &&
        echo '  Window 3: UE (./run_srsran_2ue.sh)' &&
        echo '' &&
        echo 'Waiting for UE connection logs...' &&
        echo 'Looking for: \"RRC Connected\" and \"Network attach successful\"' &&
        echo '' &&
        sleep 5 &&
        echo 'Setting up traffic generator windows...' &&
        screen -S edgeric -X screen -t 'Traffic-Server' &&
        screen -S edgeric -p 'Traffic-Server' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC/traffic-generator\n' &&
        screen -S edgeric -p 'Traffic-Server' -X stuff './iperf_server_2ues.sh\n' &&
        screen -S edgeric -X screen -t 'Traffic-Client' &&
        screen -S edgeric -p 'Traffic-Client' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC/traffic-generator\n' &&
        screen -S edgeric -p 'Traffic-Client' -X stuff './iperf_client_2ues.sh 21M 5M 10000\n' &&
        echo 'Setting up EdgeRIC application windows...' &&
        screen -S edgeric -X screen -t 'Redis-Server' &&
        screen -S edgeric -p 'Redis-Server' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC/edgeric\n' &&
        screen -S edgeric -p 'Redis-Server' -X stuff 'redis-server\n' &&
        sleep 2 &&
        screen -S edgeric -X screen -t 'muApp1' &&
        screen -S edgeric -p 'muApp1' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC/edgeric/muApp1\n' &&
        screen -S edgeric -p 'muApp1' -X stuff 'redis-cli set scheduling_algorithm \"Max CQI\"\n' &&
        screen -S edgeric -p 'muApp1' -X stuff 'python3 muApp1_run_DL_scheduling.py\n' &&
        screen -S edgeric -X screen -t 'Redis-Config' &&
        screen -S edgeric -p 'Redis-Config' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC/edgeric\n' &&
        screen -S edgeric -p 'Redis-Config' -X stuff 'redis-cli set scheduling_algorithm \"Max Weight\"\n' &&
        screen -S edgeric -X screen -t 'muApp3-Monitor' &&
        screen -S edgeric -p 'muApp3-Monitor' -X stuff 'cd /home/EdgeRIC-A-real-time-RIC/edgeric/muApp3\n' &&
        screen -S edgeric -p 'muApp3-Monitor' -X stuff 'python3 muApp3_monitor_terminal.py\n' &&
        echo 'All screen sessions started:' &&
        echo '  Window 0: GNU-Radio (python3 top_block_2ue_no_gui.py)' &&
        echo '  Window 1: EPC (./run_epc.sh)' &&
        echo '  Window 2: ENB (./run_enb.sh)' &&
        echo '  Window 3: UE (./run_srsran_2ue.sh)' &&
        echo '  Window 4: Traffic-Server (./iperf_server_2ues.sh)' &&
        echo '  Window 5: Traffic-Client (./iperf_client_2ues.sh 21M 5M 10000)' &&
        echo '  Window 6: Redis-Server (redis-server)' &&
        echo '  Window 7: muApp1 (muApp1_run_DL_scheduling.py)' &&
        echo '  Window 8: Redis-Config (redis-cli set scheduling_algorithm)' &&
        echo '  Window 9: muApp3-Monitor (muApp3_monitor_terminal.py)' &&
        echo '' &&
        echo 'Use \"screen -r edgeric\" to attach to screen session' &&
        echo 'Navigation: Ctrl+a then n (next), Ctrl+a then p (previous), Ctrl+a then d (detach)' &&
        echo 'Window navigation: Ctrl+a then 0-9 (go to specific window)' &&
        echo '' &&
        echo 'NOTE: Monitor Window 3 (UE) for connection logs before traffic starts' &&
        echo 'NOTE: Redis server starts in Window 6, then EdgeRIC apps in Windows 7-9' &&
        echo '' &&
        bash
    "
