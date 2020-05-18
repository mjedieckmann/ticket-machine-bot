import time
import torch
import numpy as np
from scipy.io.wavfile import write
import IPython.display as ipd
import matplotlib.pylab as plt

import warnings
from text import text_to_sequence
from melgan.model.generator import Generator
from melgan.utils.hparams import load_hparam

from hyper_parameters import tacotron_params
from training import load_model

warnings.filterwarnings("ignore")

import sys

import simpleaudio as sa

vocoder_model = None
model = None

# where the clip file will be written:
save_path = '/home/max/nli_out/audio_test.wav'

# where the pre-trained model is located:
checkpoint_path = "/home/max/nli_out//checkpoint_78000"


def main():
    init()
    speak_up("Welcome to the ticket machine. What kind of ticket would you like to purchase today?")


def init():
    global vocoder_model, model
    print("All basic modules loaded!")

    torch.manual_seed(1234)

    hparams = tacotron_params
    MAX_WAV_VALUE = 32768.0

    print("All needed functions loaded!")

    # load trained tacotron2 + GST model:
    model = load_model(hparams)
    checkpoint_path = "/home/max/nli_out/checkpoint_78000"
    model.load_state_dict(torch.load(checkpoint_path)['state_dict'])
    model.to('cuda')
    _ = model.eval()

    print("Tacotron2 loaded successfully...")

    # melgan mel2wav:

    # load pre trained MelGAN model for mel2audio:
    vocoder_checkpoint_path = "/home/max/nli_out/nvidia_tacotron2_LJ11_epoch6400.pt"
    checkpoint = torch.load(vocoder_checkpoint_path)
    hp_melgan = load_hparam("/home/max/nli_out/default.yaml")
    vocoder_model = Generator(80)  # Number of mel channels
    vocoder_model.load_state_dict(checkpoint['model_g'])
    vocoder_model = vocoder_model.to('cuda')
    vocoder_model.eval(inference=False)

    print("MelGAN vocoder loaded successfully.")

    torch.manual_seed(1234)


def speak_up(text):
    global is_talking
    print(text)
    gst_head_scores = np.array([0.30, 0.50, 0.20])
    gst_scores = torch.from_numpy(gst_head_scores).cuda().float()
    print('Input sequence and GST weights loaded...')

    torch.manual_seed(1234)

    sequence = np.array(text_to_sequence(text, ['english_cleaners']))[None, :]
    sequence = torch.from_numpy(sequence).to(device='cuda', dtype=torch.int64)
    print("Input text sequence pre-processed successfully...")

    # text2mel:
    t1 = time.time()
    with torch.no_grad():
        mel_outputs, mel_outputs_postnet, _, alignments = model.inference(sequence,
                                                                          gst_scores)
    elapsed = time.time() - t1
    print('Time elapsed in transforming text to mel has been {} seconds.'.format(elapsed))

    # mel2wav inference:
    t1 = time.time()
    with torch.no_grad():
        audio = vocoder_model.inference(mel_outputs_postnet)

    audio_numpy = audio.data.cpu().detach().numpy()
    elapsed_melgan = time.time() - t1

    print('Time elapsed in transforming mel to wav has been {} seconds.'.format(elapsed_melgan))

    write(save_path, 22050, audio_numpy)
    ipd.Audio(audio_numpy, rate=22050)

    return sa.WaveObject.from_wave_file(save_path)


if __name__ == '__main__':
    main()
