from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

KAFKA_BOOTSTRAP_SERVERS = '172.25.0.13:29092'
KAFKA_TOPIC_NAME = "sales_topic"

#postgresql connection variables
post_host_name = '172.25.0.18'
post_port_no = '5432'
post_database_name = 'sales_db'
post_driver_class = 'org.postgresql.Driver'
post_table_name_1 = "sales"
post_table_name_2 = "stocks"
post_user_name = 'superset'
post_password = 'superset'
post_jdbc_url = 'jdbc:postgresql://' + post_host_name + ':' + post_port_no + '/' + post_database_name

#save into sales table
def save_to_sales(sales_df_save):
    db_credentials = {'user': post_user_name,
                      'password': post_password,
                      'driver': post_driver_class}
    sales_df_save \
        .write \
        .jdbc(url=post_jdbc_url,
              table=post_table_name_1,
              mode='append',
              properties=db_credentials)

#save into stocks table
def save_to_stocks(stocks_df_save):
    db_credentials = {'user': post_user_name,
                      'password': post_password,
                      'driver': post_driver_class}
    stocks_df_save \
        .write \
        .option('truncate', 'true') \
        .jdbc(url=post_jdbc_url,
              table=post_table_name_2,
              mode='overwrite',
              properties=db_credentials)


if __name__ == "__main__":
    spark = SparkSession.builder \
        .appName("Kafka Spark Streaming Consumer") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    sales_schema = StructType() \
        .add('Sale_ID', IntegerType()) \
        .add('Product', StringType()) \
        .add('Quantity_Sold', IntegerType()) \
        .add('Each_Price', FloatType()) \
        .add('Sale_Date', TimestampType()) \
        .add('Sales', FloatType())

    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .option("subscribe", KAFKA_TOPIC_NAME) \
        .load()

    df1 = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")

    # Covert JSON in col'value' to String follow chema
    sales_df2 = df1.withColumn("value", from_json(col("value").cast("string"), sales_schema)) \
        .select(col("value.*")) 
    sales_df2.printSchema()

    # Splitting Sale_Date
    sales_df_split = sales_df2\
        .withColumn("Date", to_date(col("Sale_Date"), "yyyy-MM-dd")) \
        .withColumn("Day", split(col("Date"), "-").getItem(2).cast("integer")) \
        .withColumn("Month", split(col("Date"), "-").getItem(1).cast("integer")) \
        .withColumn("Year", split(col("Date"), "-").getItem(0).cast("integer")) \
        .drop("Sale_Date")
    print('Printing Schema of sales_df_split: ')
    sales_df_split.printSchema()

    filepath = "/home/jovyan/work/data_processed/Stock_Quantity.csv"
    stocks_df = spark.read.csv(filepath, header=True, inferSchema=True)

    # Drop unnecessary column for stocks table
    stocks_df_drop = sales_df2\
        .drop("Sale_ID")\
        .drop("Each_Price")\
        .drop("Sale_Date")\
        .drop("Sales")

    # Join with stocks_df
    stocks_df_join = stocks_df.join(stocks_df_drop, on="Product", how="inner")
    print('Printing Schema of stocks_df_join: ')
    stocks_df_join.printSchema()

    # GroupBy by Product
    stocks_df_group = stocks_df_join\
        .groupBy("Product", "Stock_Quantity")\
        .agg({'Quantity_Sold': 'sum'})\
        .select('Product', 'Stock_Quantity', col('sum(Quantity_Sold)').alias('Total_Quantity_Sold'))
    print('Printing Schema of stocks_df_group: ')
    stocks_df_group.printSchema()

    # write to console to debug
    sales_data_write_stream = sales_df_split \
        .writeStream \
        .trigger(continuous='1 seconds') \
        .outputMode('update') \
        .option('truncate', 'false') \
        .format('console') \
        .start()

    # Write sales data to mongodb as backup
    sales_df2\
    .writeStream \
    .format("mongodb")\
    .option("checkpointLocation", "/home/jovyan/work/mongo_checkPoint")\
    .option('spark.mongodb.connection.uri', 'mongodb://root:example@mongo:27017')\
    .option('spark.mongodb.database', 'sales_db')\
    .option('spark.mongodb.collection', 'sales_backup')\
    .trigger(processingTime='5 seconds') \
    .outputMode('append')\
    .start()

    sales_df_split\
        .writeStream\
        .trigger(processingTime='5 seconds')\
        .outputMode('update')\
        .foreachBatch(save_to_sales)\
        .start()

    stocks_df_group\
        .writeStream\
        .trigger(processingTime='5 seconds')\
        .outputMode('complete')\
        .option('truncate', 'true')\
        .foreachBatch(save_to_stocks)\
        .start()
        

    sales_data_write_stream.awaitTermination()
    print('Streaming completed!')
