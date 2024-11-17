from kafka import KafkaProducer
import time
from json import dumps
import pandas as pd

KAFKA_TOPIC_NAME = "sales_topic"
KAFKA_BOOTSTRAP_SERVERS = '172.25.0.13:29092'

if __name__ == "__main__":
    print("Kafka Producer Started ...")
    kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                                    value_serializer=lambda x: dumps(x).encode('utf-8'))
    file_path = "/home/jovyan/work/data_processed/Processed_Data.csv"
    sales_df = pd.read_csv(file_path)
    sales_list = sales_df.to_dict(orient="records")

    for sale in sales_list:
        kafka_producer.send(KAFKA_TOPIC_NAME, value=sale)
        print("Message to be sent: ", sale)
        time.sleep(1)

    