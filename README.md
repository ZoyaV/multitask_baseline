# SampleFactory APPO baseline for Iglu


## Installation
Just install all dependencies using:
```bash
pip install -r docker/requirements.txt
```


## Docker 
We use [crafting](https://pypi.org/project/crafting/) to automate our experiments. 
You can find an example of running such a pipeline in ```run.yaml``` file. 
You need to have installed Docker, Nvidia drivers, and crafting package. 

The crafting package is available in PyPI:
```bash
pip install crafting
```


To build the image run the command below in ```docker``` folder:
```bash
sh build.sh
```

To run an experiment specify target command in ```command``` field in ```run.yaml``` file and call crafting:
```bash
crafting run.yaml
```

Example of ```run.yaml``` file ():
```yaml
container:
  image: "treechop-appo-baseline:latest"
  command: 'python main.py --config_path iglu_baseline.yaml'
  tty: True
  environment:
    - "WANDB_API_KEY=<YOUR API KEY>"
    - "OMP_NUM_THREADS=1"
    - "MKL_NUM_THREADS=1"
    - "NVIDIA_VISIBLE_DEVICES=0"
code:
  folder: "."

host_config:
  runtime: nvidia
  shm_size: 4g
  mem_limit: 32g
```

Please specify your <WANDB_API_KEY> if you want to save logs in wandb cloud or turn off wandb in the training config.

## Training APPO
Just run ```train.py``` with config_path:
```bash
python main.py --config_path iglu_baseline.yaml
```
## Enjoy baseline
Run ```enjoy.py``` :
```bash
python utils/enjoy.py
```

## Per-skill aggregation of the baselines performance metrics. 
For each task, we calculate F1 score between built and target structures. 
For each skill, we average the performance on all targets requiring that skill.

| F1 score        | flying |tall |diagonal | flat   | tricky | all  |
|-----------------| ----- | -----| -------|--------|-------|------|
| MHB agent (NLP) | 0.292 | 0.322 | 0.242  |  0.334 | 0.295 | 0.313 |
| MHB agent (full)| 0.233 |0.243  | 0.161  |0.290   |  0.251|  0.258|
| Random agent (full)| 0.039|0.036  | 0.044  |0.038   |  0.043|  0.039|

