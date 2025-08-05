echo "Clearing log for fresh start"
echo "NEW LOG" > /workspaces/chat-ui-11/backend/logs/app.jsonl

cd /workspaces/chat-ui-11
source venv/bin/activate
cd frontend
npm run build
cd ../backend

pkill python
pkill uvicorn

uvicorn main:app &
echo "Server started"


# print every 3 seconds saying it is running. do 10 times. print second since start
for ((i=1; i<=10; i++)); do
    echo "Server running for $((i * 3)) seconds"
    sleep 3
done

# wait X seconds. 
# waittime=10
# echo "Starting server, waiting for $waittime seconds before sending config request"
# for ((i=waittime; i>0; i--)); do
#     echo "Waiting... $i seconds remaining"
#     sleep 1
# done
# host=127.0.0.1
# echo "Sending config request to $host:8000/api/config"
# result=$(curl -X GET http://$host:8000/api/config -H "Content-Type: application/json" -d '{"key": "value"}')
# # use json format output in a pretty way


# # echo "Config request sent, result:"
# # echo $result | jq .
# # # print the result
# # echo "Config request result: $(echo $result | jq .)
# # "

# # just get the "tools" part of the result and prrety print it
# echo "Config request result: $(echo $result | jq '.tools')"

# # make a count for 20 seconds and prompt the human to cause any errors
# echo "server ready, you can now cause any errors in the UI"
# for ((i=20; i>0; i--)); do
#     echo "You have $i seconds to cause any errors in the UI"
#     sleep 1
# done