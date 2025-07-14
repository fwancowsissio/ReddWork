
from pyspark.sql import SparkSession
from pyspark.ml.feature import RegexTokenizer, HashingTF, StringIndexer, IndexToString
from pyspark.ml.classification import LogisticRegression
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator

# Start a Spark session
spark = SparkSession.builder.appName("SkillClassifier").getOrCreate()

# Load the dataset from CSV
df = spark.read.option("header", True).csv("traindata.csv")

# Drop rows with missing 'skills' or 'category'
df = df.na.drop(subset=["skills", "category"])

# Convert string labels (categories) to numeric labels
label_indexer = StringIndexer(inputCol="category", outputCol="label")
fitted_label_indexer = label_indexer.fit(df)

# Tokenize the 'skills' column by splitting on commas
tokenizer = RegexTokenizer(inputCol="skills", outputCol="tokens", pattern=",", toLowercase=False)

# Apply HashingTF (term frequency) to convert tokens into feature vectors
hashingTF = HashingTF(inputCol="tokens", outputCol="features", numFeatures=20000)

# Define the Logistic Regression model
lr = LogisticRegression(maxIter=100)

# Convert numeric predictions back to original string categories
label_converter = IndexToString(inputCol="prediction", outputCol="predicted_category",
                                labels=fitted_label_indexer.labels)

# Define the full ML pipeline
pipeline = Pipeline(stages=[
    fitted_label_indexer,
    tokenizer,
    hashingTF,
    lr,
    label_converter
])

# Split the data into training and test sets (80% train, 20% test)
train_data, test_data = df.randomSplit([0.8, 0.2], seed=42)

# Define a parameter grid for hyperparameter tuning
paramGrid = ParamGridBuilder() \
    .addGrid(lr.maxIter, [50, 100]) \
    .addGrid(lr.regParam, [0.01, 0.1]) \
    .build()

# Define an evaluator using accuracy
evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="accuracy")

# Set up cross-validation with 3 folds
cv = CrossValidator(estimator=pipeline,
                    estimatorParamMaps=paramGrid,
                    evaluator=evaluator,
                    numFolds=3)

# Train the model with cross-validation
cv_model = cv.fit(train_data)

# Evaluate the model on the test set
predictions = cv_model.transform(test_data)
accuracy = evaluator.evaluate(predictions)
print(f"Accuracy: {accuracy:.4f}")

# Show example predictions
predictions.select("skills", "category", "predicted_category").show(truncate=100)

# Save the best model from cross-validation
cv_model.bestModel.save("spark_model")

# Stop the Spark session
spark.stop()
