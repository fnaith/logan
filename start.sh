PORT=5000

nohup python3 -m flask run -p $PORT -h localhost > /dev/null 2>&1 &
