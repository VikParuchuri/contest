from __future__ import division
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
import re
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from scipy.sparse import hstack
from sklearn.feature_selection import chi2, f_regression
from sklearn.feature_selection import SelectKBest
import string

class Algorithm(object):
    """
    This class is imported and called by test.py.
    It is used to train the classifier and run predictions.
    You can edit the class (and add and import other files in the repo, also).
    Be sure not to change the function signature of __init__, train, predict, generate_df, or generate_features.
    If you do, your submission will fail.
    """

    def __init__(self):
        """
        Initialize any specific algorithm-related variables here.
        """

        # Create a new classifier.
        self.clf = Ridge()
        # Create a vectorizer to extract features.
        # Important to make this a class attribute, as the vocab needs to be the same for train and prediction sets.
        self.vectorizer = Pipeline([
            ('vect', CountVectorizer(min_df=20, stop_words="english", ngram_range=(1,2))),
            ('tfidf', TfidfTransformer())
        ])
        self.collist = []

    def generate_df(self, data):
        """
        Generate a pandas dataframe from the raw input data.
        :param data: Review data read in from text files.
        :return: A pandas dataframe, where each row is a review, and contains all the needed information.
        """
        # Split the data into sections (what will become df rows)
        rows = data.split("\n\n")

        matrix = []
        # Read in the data section by section.
        for r in rows:
            new_row = []
            # Split each section into lines.
            for i, l in enumerate(r.strip().split("\n")):
                # Strip out the beginning of the line, which indicates which field it is.
                l = re.sub("[a-z]+/[a-zA-Z]+: ", "", l)
                # Convert to unicode.
                l = unicode(l, errors='replace')

                # Some scores are not numbers -- convert them.
                if i == 2:
                    if l == "1/2":
                        l = "2"
                    elif l == "0/0":
                        l = "0"
                    elif l == "2/2":
                        l = "5"
                new_row.append(l)
            # Add the row into the new matrix.
            matrix.append(new_row[:5])
        # Convert the list of lists into a pandas dataframe
        df = pd.DataFrame(matrix, columns=["product_id", "helpfulness", "score", "summary", "text"])
        df["score"] = df["score"].astype(float)
        df["text"] = [t.lower() for t in df["text"]]
        return df

    def generate_features(self, df, type="train"):
        """
        Generate the textual features needed to train or predict data.
        Called when generating the dataframe to either train the algorithm, or predict using it.
        :param df: A dataframe containing the extracting test or training data.
        :param type: A string indicating what type of features should be made.  Either "train" for training set, or "test" for test set.
        :return: A matrix or pandas dataframe containing the features.
        """
        # Extract features.
        if type == "train":
            algorithmic_features = self.vectorizer.fit_transform(df["text"])
        else:
            algorithmic_features = self.vectorizer.transform(df["text"])

        # Define some functions that can transform the text into features.
        transform_functions = {
            "length": lambda x: len(x),
            "exclams": lambda x: x.count("!"),
            "question_marks": lambda x: x.count("?"),
            "sentences": lambda x: x.count("."),
            # Add one as a smooth.
            "words_per_sentence": lambda x: x.count(" ") / (x.count(".") + 1),
            "letters_per_word": lambda x: len(x) / (x.count(" ") + 1),
            "commas": lambda x: x.count(","),
        }

        # Create a list of pandas columns.
        # This guarantees order -- dictionaries may not.
        hand_features_list = []
        hand_feature_names = []

        for col in ["text", "summary"]:
            for name, func in transform_functions.iteritems():
                hand_features_list.append(df[col].apply(func))
                hand_feature_names.append("{0}_{1}".format(col, name))

        hand_chosen_features = pd.concat(hand_features_list, axis=1)
        hand_chosen_features.columns = hand_feature_names

        features = hstack([algorithmic_features, hand_chosen_features])

        if type == "train":
            # Select 1000 "best" columns based on chi squared.
            selector = SelectKBest(chi2, k=2000)
            selector.fit(features, df["score"])
            self.collist = selector.get_support().nonzero()

        # Grab chi squared selected column subset.
        features = features.tocsc()[:, self.collist[0]].todense()
        return features

    def train(self, feats, to_predict):
        """
        Train a prediction algorithm.
        :param feats: The training features.
        :param to_predict: A pandas series or numpy array containing the column to predict.
        :return: None
        """

        # Fit the regressor (train it) with our selected columns, and try to predict the to_predict column.
        self.clf.fit(feats, to_predict)

    def predict(self, feats):
        """
        Predict values for new data.
        :param feats: The features to make predictions using.  Must have the exact same columns as the feats passed to the train function.
        :return: The predictions for the to_predict column on df.
        """

        # Generate the predictions.
        predictions = self.clf.predict(feats).clip(0.1, 4.9)
        return predictions
