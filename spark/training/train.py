from pyspark.sql import SparkSession
from pyspark.ml.feature import RegexTokenizer, HashingTF, IDF, StringIndexer, IndexToString
from pyspark.ml.classification import LogisticRegression
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator

# Avvia Spark
spark = SparkSession.builder.appName("SkillClassifier").getOrCreate()

# Carica il dataset
df = spark.read.option("header", True).csv("traindata.csv")
df = df.na.drop(subset=["skills", "category"])

# StringIndexer per la categoria
label_indexer = StringIndexer(inputCol="category", outputCol="label")
fitted_label_indexer = label_indexer.fit(df)

# RegexTokenizer: split su virgola
tokenizer = RegexTokenizer(inputCol="skills", outputCol="tokens", pattern=",", toLowercase=False)

# TF-IDF
hashingTF = HashingTF(inputCol="tokens", outputCol="rawFeatures", numFeatures=20000)
idf = IDF(inputCol="rawFeatures", outputCol="features")

# Modello
lr = LogisticRegression(maxIter=100)

# Decodifica etichette
label_converter = IndexToString(inputCol="prediction", outputCol="predicted_category",
                                labels=fitted_label_indexer.labels)

# Pipeline
pipeline = Pipeline(stages=[
    fitted_label_indexer,
    tokenizer,
    hashingTF,
    idf,
    lr,
    label_converter
])

# Split
train_data, test_data = df.randomSplit([0.8, 0.2], seed=42)

# Tuning
paramGrid = ParamGridBuilder() \
    .addGrid(lr.maxIter, [50, 100]) \
    .addGrid(lr.regParam, [0.01, 0.1]) \
    .build()

# Valutatore e cross-validation
evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="accuracy")

cv = CrossValidator(estimator=pipeline,
                    estimatorParamMaps=paramGrid,
                    evaluator=evaluator,
                    numFolds=3)

# Addestramento
cv_model = cv.fit(train_data)

# Valutazione
predictions = cv_model.transform(test_data)
accuracy = evaluator.evaluate(predictions)
print(f"✅ Accuracy: {accuracy:.4f}")

# Esempi di predizione
predictions.select("skills", "category", "predicted_category").show(truncate=100)

# Salva il modello
cv_model.bestModel.save("spark_model")

spark.stop()
