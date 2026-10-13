default: main

clean:
	rm -f main

main: main.c Makefile
	gcc -Wall -g -O0 -fno-stack-protector $< -o $@
