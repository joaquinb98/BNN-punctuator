from __future__ import division

import models, data, main
import re

import sys
import codecs

import tensorflow as tf
import numpy as np
import re

MAX_SUBSEQUENCE_LEN = 200

EOS_PUNCTS = {".": ".PERIOD", "?": "?QUESTIONMARK", "!": "!EXCLAMATIONMARK"}
INS_PUNCTS = {",": ",COMMA", ";": ";SEMICOLON", ":": ":COLON"}

def to_array(arr, dtype=np.int32):
    return np.array([arr], dtype=dtype).T

def restore(text, word_vocabulary, reverse_punctuation_vocabulary, model):
    i = 0

    res = ""

    while True:

        subsequence = text[i:i+MAX_SUBSEQUENCE_LEN]

        if len(subsequence) == 0:
            break

        converted_subsequence = [ word_vocabulary["<NUM>"] if re.fullmatch('\d+', w) else word_vocabulary.get(w, word_vocabulary[data.UNK]) for w in subsequence]

        y = predict(to_array(converted_subsequence), model)


        res += subsequence[0]


        last_eos_idx = 0
        punctuations = []
        for y_t in y:

            p_i = np.argmax(tf.reshape(y_t, [-1]))
            punctuation = reverse_punctuation_vocabulary[p_i]

            punctuations.append(punctuation)

            if punctuation in data.EOS_TOKENS:
                last_eos_idx = len(punctuations) 
        
        if last_eos_idx != 0:
            step = last_eos_idx
        else:
            step = len(subsequence) - 1

        for j in range(step):
            if punctuations[j][0] in EOS_PUNCTS:
                head = ' ' + subsequence[1+j][0].upper() if j < step - 1 else ' '
                tail = subsequence[1+j][1:].lower() if j < step - 1 and len(subsequence[1+j]) > 1 else ' '
                res += punctuations[j][0] + head + tail
            
            elif j < step - 1 and converted_subsequence[1+j] == word_vocabulary[data.UNK]:
                head = ' ' if punctuations[j] == data.SPACE else punctuations[j][0]
                tail = ' ' + subsequence[1+j][0].upper() + (subsequence[1+j][1:].lower() if len(subsequence[1+j]) > 1 else ' ')
                res += head + tail 
            else:
                head = ' ' if punctuations[j] == data.SPACE else punctuations[j][0]
                tail = ' ' + subsequence[j+1].lower() if j < step - 1 else ' '
                res += head + tail

        if subsequence[-1] == data.END:
            break
        
        i += step

    return res[0].upper() + (res[1:] if len(res) > 1 else ' ')

def predict(x, model):
    return tf.nn.softmax(net(x))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        model_file = sys.argv[1]
    else:
        sys.exit("Model file path argument missing")

    if len(sys.argv) > 2:
        input_file = sys.argv[2]
    else:
        sys.exit("Input file path argument missing")

    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    else:
        sys.exit("Output file path argument missing")

    vocab_len = len(data.read_vocabulary(data.WORD_VOCAB_FILE))
    x_len = vocab_len if vocab_len < data.MAX_WORD_VOCABULARY_SIZE else data.MAX_WORD_VOCABULARY_SIZE + data.MIN_WORD_COUNT_IN_VOCAB
    x = np.ones((x_len, main.MINIBATCH_SIZE)).astype(int)

    print("Loading model parameters...")
    net, _ = models.load(model_file, x)

    print("Building model...")

    word_vocabulary = net.x_vocabulary
    punctuation_vocabulary = net.y_vocabulary

    reverse_word_vocabulary = {v:k for k,v in word_vocabulary.items()}
    reverse_punctuation_vocabulary = {v:k for k,v in punctuation_vocabulary.items()}

    print("Restoring punctuation...")
    with codecs.open(input_file, 'r', 'utf-8') as f:
        lines = f.readlines()

    if len(lines) == 0:
        sys.exit("Input file empty.")

    with open(output_file, 'w') as fout:
      fout.write("")
    with open(output_file, 'a') as fout:
      li = 0
      for l in lines:
        if li % 1000 == 0:
            print(f"line{li}")
        input_text = re.sub('\s+', ' ', l.strip())
        text = [w for w in input_text.split() if w not in punctuation_vocabulary and w not in data.PUNCTUATION_MAPPING] + ["<BREAK>", data.END]
        punct_text = restore(text, word_vocabulary, reverse_punctuation_vocabulary, net)
        fout.write(re.sub('<BREAK>|<break>' , '', punct_text.strip())+'\n')
        li += 1

