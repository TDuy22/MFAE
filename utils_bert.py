"""
Utility functions for training and validating models.
"""
import time
import torch
import torch.nn as nn
from tqdm import tqdm
from mfae.utils import correct_predictions
from transformers import BertTokenizer, BertModel

# Initialize BERT tokenizer and model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
bert_model = BertModel.from_pretrained('bert-base-uncased')

def train(model,
          dataloader,
          optimizer,
          criterion,
          epoch_number,
          max_gradient_norm):
    """
    Train a model for one epoch on some input data with a given optimizer and
    criterion.

    Args:
        model: A torch module that must be trained on some input data.
        dataloader: A DataLoader object to iterate over the training data.
        optimizer: A torch optimizer to use for training on the input model.
        criterion: A loss criterion to use for training.
        epoch_number: The number of the epoch for which training is performed.
        max_gradient_norm: Max. norm for gradient norm clipping.

    Returns:
        epoch_time: The total time necessary to train the epoch.
        epoch_loss: The training loss computed for the epoch.
        epoch_accuracy: The accuracy computed for the epoch.
    """
    # Switch the model to train mode.
    model.train()
    device = model.device

    epoch_start = time.time()
    batch_time_avg = 0.0
    running_loss = 0.0
    correct_preds = 0
    total_num = 0
    sub_len = 0

    print('aaaaaaaaaaaaaaaaaaaaaaaa')
    batch = dataloader
    tqdm_batch_iterator = tqdm(range(len(dataloader['labels'])))
    print('11111111111111111111111111')
    for batch_index in tqdm_batch_iterator:
        batch_start = time.time()

        # Tokenize and encode premises and hypotheses using Hugging Face's BERT
        premises_tokens = tokenizer(batch["premises"][batch_index], return_tensors="pt", padding=True, truncation=True)
        hypotheses_tokens = tokenizer(batch["hypotheses"][batch_index], return_tensors="pt", padding=True, truncation=True)

        # Move input and output data to the GPU if it is used.
        premises = bert_model(**premises_tokens).last_hidden_state.to(device)
        hypotheses = bert_model(**hypotheses_tokens).last_hidden_state.to(device)
        labels = torch.tensor(batch["labels"][batch_index]).to(device)

        optimizer.zero_grad()

        logits, probs = model(premises, hypotheses)
        loss = criterion(logits, labels)
        loss.backward()

        nn.utils.clip_grad_norm_(model.parameters(), max_gradient_norm)
        optimizer.step()
        batch_time_avg += time.time() - batch_start
        running_loss += loss.item()
        correct_preds += correct_predictions(probs, labels)
        total_num += len(labels)
        description = "Avg. batch proc. time: {:.4f}s, loss: {:.4f}"\
                      .format(batch_time_avg/(batch_index+1),
                              running_loss/(batch_index+1))
        tqdm_batch_iterator.set_description(description)

    epoch_time = time.time() - epoch_start
    epoch_loss = running_loss / (len(dataloader['labels']) - sub_len)
    epoch_accuracy = correct_preds / total_num

    return epoch_time, epoch_loss, epoch_accuracy


def validate(model, dataloader, criterion):
    """
    Compute the loss and accuracy of a model on some validation dataset.

    Args:
        model: A torch module for which the loss and accuracy must be
            computed.
        dataloader: A DataLoader object to iterate over the validation data.
        criterion: A loss criterion to use for computing the loss.

    Returns:
        epoch_time: The total time to compute the loss and accuracy on the
            entire validation set.
        epoch_loss: The loss computed on the entire validation set.
        epoch_accuracy: The accuracy computed on the entire validation set.
    """
    # Switch to evaluate mode.
    model.eval()
    device = model.device

    epoch_start = time.time()
    running_loss = 0.0
    running_accuracy = 0.0
    total_num = 0
    sub_len = 0

    batch = dataloader
    print('aaaaaaaaaaaa3')
    
    # Deactivate autograd for evaluation.
    with torch.no_grad():
        for batch_index in range(len(dataloader['labels'])):
            # Tokenize and encode premises and hypotheses using Hugging Face's BERT
            premises_tokens = tokenizer(batch["premises"][batch_index], return_tensors="pt", padding=True, truncation=True)
            hypotheses_tokens = tokenizer(batch["hypotheses"][batch_index], return_tensors="pt", padding=True, truncation=True)

            # Move input and output data to the GPU if one is used.
            premises = bert_model(**premises_tokens).last_hidden_state.to(device)
            hypotheses = bert_model(**hypotheses_tokens).last_hidden_state.to(device)
            labels = torch.tensor(batch["labels"][batch_index]).to(device)

            logits, probs = model(premises, hypotheses)
            loss = criterion(logits, labels)

            running_loss += loss.item()
            running_accuracy += correct_predictions(probs, labels)
            total_num += len(labels)

    epoch_time = time.time() - epoch_start
    epoch_loss = running_loss / (len(dataloader['labels']) - sub_len)
    epoch_accuracy = running_accuracy / total_num

    return epoch_time, epoch_loss, epoch_accuracy
