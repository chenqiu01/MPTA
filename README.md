# MPTA

Code for the paper "Enhanced Equilibria-Solving via Private Information Pre-Branch Structure in Adversarial Team Games" (published on [ariXiv](https://arxiv.org/pdf/2408.02283) and UAI 2025.

Our code is built upon the [open-source platform](https://github.com/TommasoBianchi/CFR-Jr) contributed by Tommaso Bianchi.

## Usage

- Choose the algorithm: CFR or CFR+. In `runner.py`, set the `--algorithm` argument to either `cfr` or `cfr+`.

- Set the number of players, ranks, and suits. In `runner.py`, configure the following arguments:
    - `--players`: Number of players.
    - `--rank`: Number of ranks (e.g., 3 for 3-player poker).
    - `--suits`: Number of suits (e.g., 4 for hearts, diamonds, clubs, spades).

- Choose stopping condition: number of iterations or time limit.
In `cfr.py`, modify the `check_fun` function to set the stopping criterion. You can stop the CFR iteration based on:

    - A fixed number of iterations.
    - A predefined time limit.  `stop_time`: the total runtime limit (in seconds); `checkEveryTime`: how frequently to output logs.


The entry point of the code is the python script `runner.py`.
It currently supports `{CFR, CFR+}` as regret-minimization algorithms, which can be run on instances of the game varients of `{Kuhn, Leduc, Goofspiel}`.
