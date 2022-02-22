echo "Stopping..."
PORT=5000
PID=$(ps -ef | grep "flask" | grep $PORT | awk '{print $2}')

if [ -z "$PID" ]; then
  echo "The target is not working now."
  exit
fi

kill -TERM $PID

COUNT=1
while [ -n "$PID" ] ; do
  if [ $COUNT -ge "5" ] ; then
    echo "Sends 'Kill' signal to process $PID"
    kill -9 $PID
  fi
  echo "Waiting more..."
  let COUNT=$COUNT+1
  sleep 2
  PID=$(ps -ef | grep "flask" | grep $PORT | awk '{print $2}')
done

echo "Stops successfully."
