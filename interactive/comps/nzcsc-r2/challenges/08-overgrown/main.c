#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

void setup(void)
{
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
}

/* Read a line into buf (at most n bytes, always NUL-terminated). */
void read_line(char *buf, int n)
{
    if (!fgets(buf, n, stdin))
        buf[0] = '\0';
    buf[strcspn(buf, "\n")] = '\0';
}

/* Load and print the flag */
void win(void)
{
    FILE *f = fopen("flag.txt", "r");
    if (!f) {
        puts("flag.txt is missing");
        exit(EXIT_FAILURE);
    }

    char buf[100] = { 0 };

    fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);

    printf("The flag is %s\n", buf);
    exit(EXIT_SUCCESS);
}


int main(void)
{
    setup();

    puts("=== overgrown ===");

    char line[100];
    unsigned long gate_three = 0x1337;
    unsigned long gate_two = 0xdead;
    unsigned long gate_one = 0;

    printf("\n> ");
    read_line(line, 0x100);

    printf("Thanks you said\n> %s\n", line);

    if (gate_one == 0) {
        return 0;
    }

    if (gate_two == 0x7465737431323334) {
        if (gate_three == 0x64726f7773734070) {
            win();
        } else {
            printf("Gate Three failed - you said 0x%lx\n", gate_three);
        }
    } else {
        printf("Gate Two failed - you said 0x%lx\n", gate_two);
    }
    return 0;
}
