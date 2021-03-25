import cv2
import math
import numpy as np
import librosa
from moviepy.editor import *


def noise(data):
    noise_amp = 0.035*np.random.uniform()*np.amax(data)
    data = data + noise_amp*np.random.normal(size=data.shape[0])
    return data


def stretch(data, rate=0.8):
    return librosa.effects.time_stretch(data, rate)


def shift(data):
    shift_range = int(np.random.uniform(low=-5, high=5)*1000)
    return np.roll(data, shift_range)


def pitch(data, sampling_rate, pitch_factor=0.7):
    return librosa.effects.pitch_shift(data, sampling_rate, pitch_factor)


def extract_features(data, sample_rate):
    # ZCR
    result = np.array([])
    zcr = np.mean(librosa.feature.zero_crossing_rate(y=data).T, axis=0)
    result = np.hstack((result, zcr))  # stacking horizontally

    # Chroma_stft
    stft = np.abs(librosa.stft(data))
    chroma_stft = np.mean(librosa.feature.chroma_stft(S=stft, sr=sample_rate).T, axis=0)
    result = np.hstack((result, chroma_stft))  # stacking horizontally

    # MFCC
    mfcc = np.mean(librosa.feature.mfcc(y=data, sr=sample_rate).T, axis=0)
    result = np.hstack((result, mfcc))  # stacking horizontally

    # Root Mean Square Value
    rms = np.mean(librosa.feature.rms(y=data).T, axis=0)
    result = np.hstack((result, rms))  # stacking horizontally

    # MelSpectrogram
    mel = np.mean(librosa.feature.melspectrogram(y=data, sr=sample_rate).T, axis=0)
    result = np.hstack((result, mel))  # stacking horizontally

    return result


def get_features(path):
    # duration and offset are used to take care of the no
    # audio in start and the ending of each audio files as seen above.
    # TODO fix this part of duration and offset
    # data, sample_rate = librosa.load(path, duration=2.5, offset=0.6)
    data, sample_rate = librosa.load(path)

    # without augmentation
    res1 = extract_features(data, sample_rate)
    result = np.array(res1)

    # data with noise
    noise_data = noise(data)
    res2 = extract_features(noise_data, sample_rate)
    result = np.vstack((result, res2))  # stacking vertically

    # data with stretching and pitching
    new_data = stretch(data)
    data_stretch_pitch = pitch(new_data, sample_rate)
    res3 = extract_features(data_stretch_pitch, sample_rate)
    result = np.vstack((result, res3))  # stacking vertically

    # data with shift
    shft_data = shift(data)
    res4 = extract_features(shft_data, sample_rate)
    result = np.vstack((result, res4))

    return result


def clip_video(video_path, start_time, end_time, save_path):
    video = VideoFileClip(video_path)
    if end_time > video.duration:
        end_time = video.duration

    video = video.subclip(start_time, end_time)
    video.write_videofile(
        save_path,
        codec='libx264',
        audio_codec='aac',
        temp_audiofile='temp-audio.m4a',
        remove_temp=True)

    del video
    return save_path


def extract_video_images(vid_path, st, et, all_data_path):
    vid_n = os.path.basename(vid_path)
    vid_name = vid_n.split(".")[0]
    num_images = 19

    save_folder = all_data_path + vid_name + '/'
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    path_to_clip = clip_video(vid_path, st, et, save_folder + vid_n)

    audio_clip = AudioFileClip(path_to_clip)
    audio_path = save_folder + vid_name + '.wav'
    audio_clip.write_audiofile(audio_path)

    audio_features = get_features(audio_path)
    np.save(save_folder + vid_name + '_features.npy', audio_features)

    cap = cv2.VideoCapture(path_to_clip)
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(length)
    interval = length // num_images
    frame_rate = cap.get(5)  # frame rate
    print(frame_rate)
    x = 1
    while cap.isOpened():
        frame_id = cap.get(1)  # current frame number
        ret, frame = cap.read()
        if not ret:
            break
        if length % num_images == 0:
            length -= 1
        if (frame_id <= (length - length % num_images)) and (frame_id % math.floor(interval) == 0):
            pic_path = all_data_path + vid_name + '/pics/'
            filename = pic_path + str(vid_name) + "_" + str(int(x)) + ".jpg"
            x += 1
            print("Frame shape Before resize", frame.shape)
            m_f_i = vid_name.split("_")
            m_f_l = m_f_i[0][-1]
            m_f_r = m_f_i[2][0]
            y1 = frame.shape[0]
            w1 = frame.shape[1]
            new_x = np.int(w1/2)
            yy = np.int(y1/4)
            if m_f_r == m_f_l:
                # Get left part of image
                frame = frame[yy: 3*yy, 0:new_x, :]
            else:
                frame = frame[yy: 3*yy, new_x:w1, :]
                # Get right part of image
            print("After", frame.shape)

            if not os.path.exists(pic_path):
                os.makedirs(pic_path)
            cv2.imwrite(filename, frame)

    cap.release()
    print("Done!")
