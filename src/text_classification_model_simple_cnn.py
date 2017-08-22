import tensorflow as tf
from tensorflow.contrib import slim
from tensorflow.contrib.layers.python.layers import layers
from configuration import *
from text_classification_model_simple import ModelSimple


class ModelSimpleCNN(ModelSimple):
    def model(self, input_text, num_output_classes, embeddings, num_hidden=TC_MODEL_HIDDEN,
              num_layers=TC_MODEL_LAYERS, dropout=TC_MODEL_DROPOUT, training=True):
        # first vector is a zeros vector used for padding
        embeddings_dimension = len(embeddings[0])
        embeddings = [[0.0] * embeddings_dimension] + embeddings
        embeddings = tf.constant(embeddings, dtype=tf.float32)
        # this means we need to add 1 to the input_text
        input_text = tf.add(input_text, 1)

        # mask to know where there is a word and where padding
        mask = tf.greater(input_text, 0)  # true for words false for padding
        # length of the sequences without padding
        sequence_length = tf.reduce_sum(tf.cast(mask, tf.int32), 1)

        embedded_sequence = tf.nn.embedding_lookup(embeddings, input_text)
        conv_sequence = layers.convolution(embedded_sequence, 128, [5], activation_fn=None)

        # Recurrent network.
        cells = []
        for _ in range(num_layers):
            cell = tf.nn.rnn_cell.GRUCell(num_hidden)
            if training:
                cell = tf.nn.rnn_cell.DropoutWrapper(cell, output_keep_prob=dropout)
            cells.append(cell)
        network = tf.nn.rnn_cell.MultiRNNCell(cells)
        sequence_output, _ = tf.nn.dynamic_rnn(network, conv_sequence, dtype=tf.float32,
                                               sequence_length=sequence_length)

        # get the last relevant output of the sequence
        batch_size = tf.shape(sequence_output)[0]
        max_length = int(sequence_output.get_shape()[1])
        output_size = int(sequence_output.get_shape()[2])
        index = tf.range(0, batch_size) * max_length + (sequence_length - 1)
        flat = tf.reshape(sequence_output, [-1, output_size])
        output = tf.gather(flat, index)
        tf.summary.histogram('dynamic_rnn_output', output)
        # apply batch normalization to speed up training time
        output = slim.batch_norm(output, scope='output_batch_norm')
        # add a full connected layer
        weight = tf.truncated_normal([num_hidden, num_output_classes], stddev=0.01)
        bias = tf.constant(0.1, shape=[num_output_classes])
        logits = tf.matmul(output, weight) + bias
        tf.summary.histogram('dynamic_rnn_logits', output)
        prediction = tf.nn.softmax(logits)

        return {
            'logits': logits,
            'prediction': prediction,
        }
