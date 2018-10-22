# bench
Docker automated testing framework

## Install

```
pip3 install git+://github.com/mattpaletta/bench.git
```

At this time, you also need to manually install 1 dependency:
```
pip3 install git+git://github.com/mattpaletta/configparser.git
```

To view all the parameters: `bench --help`

Example running:
```
bench --git https://github.com/mattpaletta/Little-Book-Of-Semaphores.git --testing_dir problems --sample_size 2
```
