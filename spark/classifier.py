import time
import pandas as pd
import re

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, from_json, concat_ws, when, size
from pyspark.sql.types import StructType, StructField, StringType, ArrayType
from pyspark.ml import PipelineModel

print("=== Avvio script streaming Kafka → Regex Skill → Elasticsearch ===")
start_total = time.time()

# === 1. Spark session ===
print("→ Inizializzo SparkSession...")
spark = SparkSession.builder.appName("KafkaSkillRegexExtractor").getOrCreate()
print("✓ SparkSession inizializzata")

# === 2. Carica lista skill ===
skills_path = "skill_list.csv"
print(f"→ Carico skill list da: {skills_path}")
start = time.time()
skill_df = pd.read_csv(skills_path)
skill_df.columns = [c.strip().lower() for c in skill_df.columns]
skills = skill_df["skill"].dropna().str.lower().unique().tolist()
print(f"✓ Skill caricate: {len(skills)} in {time.time() - start:.2f} s")

# === 3. Prepara regex e broadcast ===
print("→ Preparo regex pattern e broadcast...")
start = time.time()
escaped_skills = sorted([re.escape(skill) for skill in skills], key=len, reverse=True)
pattern = r'(?<!\w)(?:' + '|'.join(escaped_skills) + r')(?!\w)'
broadcast_pattern = spark.sparkContext.broadcast(pattern)
print(f"✓ Pattern pronto in {time.time() - start:.2f} s")

# === 4. UDF per estrazione skill con pulizia conservativa ===
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
        print(f"Errore in extract_skills: {e}")
        return []

# === 5. Schema JSON in arrivo da Kafka ===
schema = StructType([
    StructField("id", StringType()),
    StructField("title", StringType()),
    StructField("created_utc", StringType()),
    StructField("selftext", StringType())
])

# === 6. Lettura da Kafka ===
print("→ Connessione a Kafka...")
start = time.time()
df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "broker:9092") \
    .option("subscribe", "redditjob") \
    .option("startingOffsets", "earliest") \
    .load()
print(f"✓ Connesso a Kafka in {time.time() - start:.2f} s")

# === 7. Parsing JSON ===
print("→ Parsing JSON dai messaggi Kafka...")
posts = df.selectExpr("CAST(value AS STRING) as json_str") \
    .select(from_json(col("json_str"), schema).alias("data")) \
    .select("data.*")

# === 8. Prepara testo e colonna skills ===
print("→ Estraggo skill dai testi...")
posts = posts.withColumn("text", concat_ws(" ", col("title"), col("selftext")))
posts = posts.withColumn("skills_array", extract_skills(col("text")))
posts = posts.withColumn("skills", concat_ws(", ", col("skills_array")))

print("→ Carico modello ML salvato...")
model_path = "model"  # percorso modello salvato con .save()
model = PipelineModel.load(model_path)
print("✓ Modello caricato")

# === 10. Prepara input per il modello ===
# Il modello si aspetta una colonna "text", che abbiamo già

# === 11. Applica modello per predizione categoria ===
print("→ Applicazione modello per predizione categoria...")
predictions = model.transform(posts)

# === 9. Output finale ===
predictions = model.transform(posts)

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

# Scrittura su Elasticsearch
query = output.writeStream \
    .format("org.elasticsearch.spark.sql") \
    .option("es.nodes", "elasticsearch") \
    .option("es.port", "9200") \
    .option("es.resource", "predjob") \
    .option("es.mapping.id", "id") \
    .option("checkpointLocation", "/app/checkpoint") \
    .outputMode("append") \
    .start()

query.awaitTermination()
