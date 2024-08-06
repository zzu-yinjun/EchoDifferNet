# EchoDiffNet: Echo-Based Depth Estimation with Wave Conditioned Diffusion Models

This repository contains snippets of test code for [EchoDiffNet] used to demonstrate and validate the methods described in the paper. While the full research code is not released to protect project integrity and sensitive information, we provide this test code to verify the model's accuracy.

## Dataset

* **Replica-Dataset:** Available from the [Replica](https://github.com/facebookresearch/VisualEchoes) repository. We used the 128x128 image resolution for our experiments.
* **Matterport-Dataset:** An extension of the existing [Matterport3D](https://niessner.github.io/Matterport/) dataset. To obtain the raw frames, please request access from the Matterport3D authors. We will soon release the procedure for generating frames and echoes using Habitat-sim and SoundSpaces.

## Evaluation

Configure the relevant YAML files before testing. Pre-trained model parameters can be [downloaded](https://drive.google.com/file/d/15MLo6jRcxtDE-xNHwRy5lpVAwz1pBCAY/view?usp=drive_link).

To run the test script:
```
pip install -r requirements.txt
python test.py
```

