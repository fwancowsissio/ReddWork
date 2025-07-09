FROM apache/spark:3.4.4

USER root

RUN apt-get update && apt-get install -y python3-pip

RUN pip3 install pandas pyarrow

WORKDIR /app
COPY classifier.py /app/classifier.py
COPY skill_list.csv /app/skill_list.csv
COPY training/model /app/model


CMD ["/opt/spark/bin/spark-submit","--conf", "spark.driver.extraJavaOptions=-Divy.cache.dir=/ivy -Divy.home=/ivy", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.4,org.elasticsearch:elasticsearch-spark-30_2.12:8.17.0", "/app/classifier.py"]   