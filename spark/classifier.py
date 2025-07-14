
import time
import pandas as pd
import re

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, from_json, concat_ws, when, size
from pyspark.sql.types import StructType, StructField, StringType, ArrayType
from pyspark.ml import PipelineModel

print("Starting Kafka to Spark to Elasticsearch streaming pipeline")
start_total = time.time()

# Initialize Spark session
print("Initializing SparkSession")
spark = SparkSession.builder.appName("SkillCategoryExtractor").getOrCreate()
print("SparkSession initialized")

# Load skill list from CSV file
skills_path = "skill_list.csv"
print(f"Loading skill list from {skills_path}")
start = time.time()
skill_df = pd.read_csv(skills_path)
skill_df.columns = [c.strip().lower() for c in skill_df.columns]
skills = skill_df["skill"].dropna().str.lower().unique().tolist()
print(f"Loaded {len(skills)} skills in {time.time() - start:.2f} seconds")

# Prepare regular expression pattern for skill matching and broadcast to Spark workers
print("Preparing regex pattern and broadcasting")
start = time.time()
escaped_skills = sorted([re.escape(skill) for skill in skills], key=len, reverse=True)
pattern = r'(?<!\w)(?:' + '|'.join(escaped_skills) + r')(?!\w)'
broadcast_pattern = spark.sparkContext.broadcast(pattern)
print(f"Regex pattern ready in {time.time() - start:.2f} seconds")

# Define user-defined function to extract skills from text using regex pattern
@udf(ArrayType(StringType()))
def extract_skills(text):
    if not text:
        return []
    try:
        text_clean = text.lower()
        text_clean = text_clean.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        text_clean = re.sub(r'[^a-z0-9\+\#\./\-\s]', ' ', text_clean)
        text_clean = re.sub(r'\s+', ' ', text_clean).strip()
        found = re.findall(broadcast_pattern.value, text_clean)
        return found
    except Exception as e:
        print(f"Error in extract_skills: {e}")
        return []

# Define schema of JSON messages coming from Kafka
schema = StructType([
    StructField("id", StringType()),
    StructField("title", StringType()),
    StructField("created_utc", StringType()),
    StructField("selftext", StringType())
])

# Connect to Kafka and read streaming data from topic
print("Connecting to Kafka")
start = time.time()
df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "broker:9092") \
    .option("subscribe", "redditjob") \
    .option("startingOffsets", "earliest") \
    .load()
print(f"Connected to Kafka in {time.time() - start:.2f} seconds")

# Parse JSON strings from Kafka messages into structured columns
print("Parsing JSON from Kafka messages")
posts = df.selectExpr("CAST(value AS STRING) as json_str") \
    .select(from_json(col("json_str"), schema).alias("data")) \
    .select("data.*")

# Combine title and selftext into a single text column and extract skills using UDF
print("Extracting skills from text")
posts = posts.withColumn("text", concat_ws(" ", col("title"), col("selftext")))
posts = posts.withColumn("skills_array", extract_skills(col("text")))
posts = posts.withColumn("skills", concat_ws(", ", col("skills_array")))

# Load pre-trained machine learning model for category prediction
print("Loading saved ML model")
model_path = "model"
model = PipelineModel.load(model_path)
print("Model loaded")

# Apply model to predict category of job posts
print("Applying model to predict category")
predictions = model.transform(posts)

# Prepare final output including predicted category and skills
output = predictions.withColumn(
    "category",
    when(size(col("skills_array")) == 0, "other").otherwise(col("predicted_category"))
).select(
    "category",
    "id",
    "title",
    "selftext",
    "created_utc",
    "skills_array"
)

# Write results to Elasticsearch using streaming write
query = output.writeStream \
    .format("org.elasticsearch.spark.sql") \
    .option("es.nodes", "elasticsearch") \
    .option("es.port", "9200") \
    .option("es.resource", "predjob") \
    .option("es.mapping.id", "id") \
    .option("checkpointLocation", "/app/checkpoint") \
    .outputMode("append") \
    .start()

# Wait for streaming to finish
query.awaitTermination()
