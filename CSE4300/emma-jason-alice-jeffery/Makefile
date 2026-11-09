CC = gcc
CFLAGS = -Wall -Wextra -g -Iinclude

SRCS = $(wildcard src/*.c) $(wildcard src/schedulers/*.c)
OBJS = $(patsubst %.c,build/%.o,$(notdir $(SRCS)))

.PHONY: all clean

all: scheduler

scheduler: $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^

build/%.o: src/%.c | build
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/schedulers/%.c | build
	$(CC) $(CFLAGS) -c $< -o $@

build:
	mkdir -p build

clean:
	rm -rf build scheduler
