
### Table II analogue - mean over the 8 circuits (5 % key-gates; mean over 5 seeds, ± = std over seeds)

| algorithm              | metric                  | XOR/XNOR   | tristate   |   tri - xor | paper XOR | tri   |
|:-----------------------|:------------------------|:-----------|:-----------|------------:|:------------------|
| FLL                    | output_corruptibility   | 46.1 ± 0.2 | 46.0 ± 0.2 |       -0.11 | 41.9 | 42.0       |
| FLL                    | corruption_rate         | 99.7 ± 0.2 | 99.5 ± 0.2 |       -0.21 | 99.7 | 99.6       |
| FLL                    | output_coverage         | 99.2 ± 0.0 | 99.2 ± 0.0 |        0.00 | 66.6 | 70.1       |
| FLL                    | output_coverage_per_key | 77.2 ± 0.5 | 90.5 ± 0.5 |       13.26 | -                 |
| FLL                    | output_coverage_maxhd   | 87.5 ± 0.8 | 89.1 ± 0.6 |        1.55 | -                 |
| FpLL (as published)    | output_corruptibility   | 32.1 ± 0.2 | 31.9 ± 0.1 |       -0.25 | 43.5 | 43.4       |
| FpLL (as published)    | corruption_rate         | 96.1 ± 0.3 | 96.0 ± 0.4 |       -0.13 | 98.5 | 98.8       |
| FpLL (as published)    | output_coverage         | 89.6 ± 0.0 | 89.7 ± 0.1 |        0.02 | 68.9 | 71.4       |
| FpLL (as published)    | output_coverage_per_key | 85.7 ± 0.4 | 87.3 ± 0.2 |        1.54 | -                 |
| FpLL (as published)    | output_coverage_maxhd   | 67.1 ± 0.3 | 66.7 ± 0.4 |       -0.41 | -                 |
| FpLL+ (our 'improved') | output_corruptibility   | 39.4 ± 0.2 | 39.3 ± 0.2 |       -0.09 | -                 |
| FpLL+ (our 'improved') | corruption_rate         | 99.5 ± 0.1 | 99.3 ± 0.1 |       -0.15 | -                 |
| FpLL+ (our 'improved') | output_coverage         | 94.5 ± 0.6 | 94.3 ± 0.2 |       -0.20 | -                 |
| FpLL+ (our 'improved') | output_coverage_per_key | 75.6 ± 0.6 | 85.5 ± 0.3 |        9.87 | -                 |
| FpLL+ (our 'improved') | output_coverage_maxhd   | 78.4 ± 0.7 | 79.3 ± 0.5 |        0.87 | -                 |
| random (baseline)      | output_corruptibility   | 25.3 ± 0.2 | 25.3 ± 0.2 |       -0.01 | -                 |
| random (baseline)      | corruption_rate         | 94.0 ± 0.1 | 93.9 ± 0.2 |       -0.14 | -                 |
| random (baseline)      | output_coverage         | 84.1 ± 0.0 | 84.1 ± 0.0 |        0.00 | -                 |
| random (baseline)      | output_coverage_per_key | 80.3 ± 0.4 | 82.3 ± 0.3 |        1.93 | -                 |
| random (baseline)      | output_coverage_maxhd   | 60.4 ± 0.3 | 60.1 ± 0.6 |       -0.30 | -                 |


### Fig. 5 analogue - per circuit, FLL, 5 % key-gates (ours vs paper's digitised bars)

|                           |   c432 |   c1355 |   c1908 |   c3540 |   c5315 |   c7552 |    i8 |   apex4 |
|:--------------------------|-------:|--------:|--------:|--------:|--------:|--------:|------:|--------:|
| output_corruptibility XOR |   43.6 |    43.4 |    48.9 |    51.0 |    45.2 |    46.3 |  40.3 |    50.2 |
| output_corruptibility tri |   43.4 |    44.0 |    47.9 |    50.1 |    45.5 |    46.6 |  39.2 |    51.1 |
| paper corruptibility XOR  |   39.4 |    40.0 |    46.3 |    37.3 |    35.5 |    41.9 |  47.4 |    47.5 |
| paper corruptibility tri  |   40.7 |    38.4 |    46.4 |    37.2 |    39.6 |    43.3 |  45.2 |    46.0 |
| corruption_rate XOR       |   97.4 |   100.0 |   100.0 |   100.0 |   100.0 |   100.0 | 100.0 |   100.0 |
| corruption_rate tri       |   95.6 |   100.0 |   100.0 |   100.0 |   100.0 |   100.0 | 100.0 |   100.0 |
| paper corruption_rate XOR |   97.6 |   100.0 |   100.0 |   100.0 |   100.0 |   100.0 | 100.0 |   100.0 |
| paper corruption_rate tri |   97.1 |   100.0 |   100.0 |   100.0 |   100.0 |   100.0 | 100.0 |   100.0 |
| output_coverage XOR       |  100.0 |   100.0 |   100.0 |   100.0 |   100.0 |    99.1 | 100.0 |    94.7 |
| output_coverage tri       |  100.0 |   100.0 |   100.0 |   100.0 |   100.0 |    99.1 | 100.0 |    94.7 |
| paper coverage XOR        |   78.4 |    56.2 |    63.5 |    66.9 |    52.9 |    53.7 |  86.8 |    75.3 |
| paper coverage tri        |   82.3 |    60.2 |    71.9 |    67.5 |    63.8 |    55.4 |  85.4 |    75.6 |
| coverage_per_key XOR      |   79.9 |    64.3 |    77.8 |    76.4 |    74.4 |    67.3 |  93.5 |    84.2 |
| coverage_per_key tri      |   91.4 |    86.4 |    90.6 |    90.3 |    89.5 |    83.8 |  98.5 |    93.6 |


### Agreement with the paper's Fig. 5 (FLL)

| metric                  | scheme   |   mean abs. error (pts) |   Pearson r (8 circuits) |
|:------------------------|:---------|------------------------:|-------------------------:|
| output_corruptibility   | xor      |                    5.97 |                    -0.02 |
| output_corruptibility   | tri      |                    5.37 |                    -0.01 |
| corruption_rate         | xor      |                    0.03 |                     1.00 |
| corruption_rate         | tri      |                    0.18 |                     1.00 |
| output_coverage         | xor      |                   32.51 |                    -0.21 |
| output_coverage         | tri      |                   28.96 |                    -0.11 |
| output_coverage_per_key | xor      |                   10.52 |                     0.89 |
| output_coverage_per_key | tri      |                   20.23 |                     0.91 |


### Table III analogue - tristate with half the key-gates (2.5 %) vs XOR/XNOR (5 %)

| algorithm              | metric                  |   XOR 5% (ours) |   XOR 5% 4 largest (ours) |   tri 2.5% 8 circ (ours) |   tri 2.5% 4 largest (ours) | paper (XOR | 8 | 4 largest)   |
|:-----------------------|:------------------------|----------------:|--------------------------:|-------------------------:|----------------------------:|:------------------------------|
| FLL                    | output_corruptibility   |            46.1 |                      45.5 |                     41.3 |                        41.0 | 41.9 | 37.2 | 40.8            |
| FLL                    | corruption_rate         |            99.7 |                     100.0 |                     99.2 |                       100.0 | 99.7 | 97.8 | 99.7            |
| FLL                    | output_coverage         |            99.2 |                      98.5 |                     99.2 |                        98.5 | 66.6 | 67.0 | 69.8            |
| FLL                    | output_coverage_per_key |            77.2 |                      79.9 |                     87.2 |                        89.8 | -                             |
| FpLL (as published)    | output_corruptibility   |            32.1 |                      38.6 |                     29.1 |                        35.2 | 43.5 | 35.3 | 42.2            |
| FpLL (as published)    | corruption_rate         |            96.1 |                     100.0 |                     95.4 |                        99.9 | 98.5 | 98.6 | 100.0           |
| FpLL (as published)    | output_coverage         |            89.6 |                      81.6 |                     87.9 |                        80.3 | 68.9 | 66.8 | 70.8            |
| FpLL (as published)    | output_coverage_per_key |            85.7 |                      78.8 |                     85.2 |                        79.1 | -                             |
| FpLL+ (our 'improved') | output_corruptibility   |            39.4 |                      44.4 |                     35.6 |                        40.1 | -                             |
| FpLL+ (our 'improved') | corruption_rate         |            99.5 |                     100.0 |                     98.8 |                       100.0 | -                             |
| FpLL+ (our 'improved') | output_coverage         |            94.5 |                      94.8 |                     94.4 |                        94.6 | -                             |
| FpLL+ (our 'improved') | output_coverage_per_key |            75.6 |                      78.1 |                     81.9 |                        85.3 | -                             |


### Sensitivity to how Hi-Z / UNK are simulated (FLL, tristate 5 %, mean of 8 circuits)

|                    |   output_corruptibility |   corruption_rate |   output_coverage |   output_coverage_per_key |
|:-------------------|------------------------:|------------------:|------------------:|--------------------------:|
| ('const', 'buf')   |                    45.7 |              99.5 |              99.2 |                      83.6 |
| ('const', 'const') |                    45.9 |              99.5 |              99.2 |                      90.2 |
| ('const', 'inv')   |                    46.0 |              99.5 |              99.2 |                      84.6 |
| ('const', 'pin')   |                    46.0 |              99.5 |              99.2 |                      90.3 |
| ('const', 'vec')   |                    45.9 |              99.5 |              99.2 |                      90.3 |
| ('vec', 'buf')     |                    45.7 |              99.5 |              99.2 |                      83.7 |
| ('vec', 'const')   |                    45.9 |              99.5 |              99.2 |                      90.3 |
| ('vec', 'inv')     |                    46.0 |              99.4 |              99.2 |                      84.8 |
| ('vec', 'pin')     |                    45.9 |              99.6 |              99.2 |                      90.4 |
| ('vec', 'vec')     |                    45.9 |              99.5 |              99.2 |                      90.4 |
| ('zero', 'buf')    |                    43.8 |              99.7 |              99.2 |                      83.5 |
| ('zero', 'const')  |                    44.0 |              99.7 |              99.2 |                      90.2 |
| ('zero', 'inv')    |                    44.1 |              99.7 |              99.2 |                      84.6 |
| ('zero', 'pin')    |                    44.2 |              99.7 |              99.2 |                      90.2 |
| ('zero', 'vec')    |                    44.0 |              99.7 |              99.2 |                      90.3 |


For reference, XOR/XNOR with the same locations: corruptibility 46.1, rate 99.7, coverage 99.2, coverage per key 77.2.


### Claim-by-claim check

| algorithm              |   |Δ corruptibility| (paper <0.3) |   |Δ corruption rate| (paper <0.3) |   Δ coverage D1 (paper +2.5..3.5) |   Δ coverage D2 per-key |   Δ coverage D3 max-HD |
|:-----------------------|----------------------------------:|-----------------------------------:|----------------------------------:|------------------------:|-----------------------:|
| FLL                    |                              0.11 |                               0.21 |                              0.00 |                   13.26 |                   1.55 |
| FpLL (as published)    |                              0.25 |                               0.13 |                              0.02 |                    1.54 |                  -0.41 |
| FpLL+ (our 'improved') |                              0.09 |                               0.15 |                             -0.20 |                    9.87 |                   0.87 |


### Selection time (s, mean over circuits) - paper claims improved FpLL is faster

| algo      |   sel_time_s |
|:----------|-------------:|
| fll       |         0.15 |
| fpll      |         0.12 |
| fpll_plus |         0.15 |
| random    |         0    |
