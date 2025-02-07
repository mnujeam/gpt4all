from datasets import load_dataset, Dataset
import os
from torch.utils.data import DataLoader
from .preprocess import tokenize_inputs
from transformers import DefaultDataCollator


def load_retrieval_augmented_data(config, tokenizer, split="train", split_dataset=True):
    dataset_path = config["dataset_path"]

    if os.path.exists(dataset_path):
        dataset = Dataset.load_from_disk(dataset_path)
    else:
        dataset = load_dataset(dataset_path, split=split)


    question_col = config["q_column"]
    answer_col = config["a_column"]
    encoder_column = config["encoder_column"]

    if config["streaming"] is False:
        kwargs = {"num_proc": config["num_proc"]}
    else:
        kwargs = {}

    # strip any unneccessary whitespace
    # there's one question that's includes a ton of whitespace
    dataset = dataset.map(lambda ele: {question_col: [q.strip() for q in ele[question_col]]}, batched=True)
    # in squad, the data is formatted where each ele in answers is a dict where the key text holds
    # a list of the answer
    dataset = dataset.map(lambda ele: {answer_col: [t["text"][0] for t in ele[answer_col]]}, batched=True)

    dataset = dataset.map(
        lambda ele: tokenize_inputs(config, tokenizer, ele, question_col, answer_col),
        batched=True,
        **kwargs
    )

    # tokenize inputs + labels in teacher-force format
    # rename encoder hidden states if not already called that
    if encoder_column != "encoder_hidden_states":
        dataset = dataset.rename_column(encoder_column, "encoder_hidden_states")

    columns_to_keep = ["input_ids", "labels", "encoder_hidden_states"]

    col_names_to_rm = [col for col in dataset.column_names if col not in columns_to_keep]
    dataset = dataset.remove_columns(col_names_to_rm)

    if split_dataset:
        dataset = dataset.train_test_split(test_size=config["pct_test"], seed=config["seed"])
        train_dataset, val_dataset = dataset["train"], dataset["test"]

        train_dataloader = DataLoader(
            train_dataset,
            batch_size=config["batch_size"],
            collate_fn=DefaultDataCollator(),
        )

        val_dataloader = DataLoader(
            val_dataset,
            batch_size=config["batch_size"],
            collate_fn=DefaultDataCollator(),
        )

        return train_dataloader, val_dataloader

    else:
        dataloader = DataLoader(
            dataset,
            batch_size=config["batch_size"],
            collate_fn=DefaultDataCollator(),
        )

        return dataloader

