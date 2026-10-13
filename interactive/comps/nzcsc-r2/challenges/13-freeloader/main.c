#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

void load_flag(void)
{
    FILE *f = fopen("flag.txt", "r");
    if (!f) {
        puts("flag.txt is missing");
        exit(EXIT_FAILURE);
    }

    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);

    char *flag_buf = malloc(size + 1);
    if (!flag_buf) {
        puts("malloc failed");
        exit(EXIT_FAILURE);
    }

    fread(flag_buf, 1, size, f);
    fclose(f);
    flag_buf[size] = '\0';

    printf("Flag loaded into buffer at %p\n", flag_buf);

    // printf("The flag is %s\n", flag_buf)
}

char *do_alloc(void)
{
    char line[16];

    printf("Enter the size you want\n> ");
    read_line(line, sizeof(line));

    int size = atoi(line);
    if (size <= 0 || size > 4096) {
        puts("invalid size (1-4096)");
        return NULL;
    }

    char *buf = malloc(size);
    if (!buf) {
        puts("malloc failed");
        exit(EXIT_FAILURE);
    }

    printf("Buffer at %p. Enter data:\n> ", buf);
    read_line(buf, size);
    puts("Data written.");

    return buf;
}

void do_print(char *buf)
{
    if (!buf) {
        puts("No buffer allocated.");
        return;
    }

    printf("Buffer at %p:\n", (void *)buf);
    puts(buf);
}

void do_free(char *buf)
{
    if (!buf) {
        puts("No buffer allocated.");
        return;
    }

    printf("Buffer at %p freed.\n", buf);
    free(buf);
    buf = NULL;
}

int main(void)
{
    setup();

    puts("=== freeloader ===");
    puts("Commands:");
    puts("  1) alloc : malloc a buffer and write data to it");
    puts("  2) print : print the buffer");
    puts("  3) free  : free the buffer");
    puts("  4) flag  : load flag.txt into a fresh buffer");
    puts("  5) exit");
    puts("");

    char line[16];
    char *buf = NULL;
    while (1) {

        printf("\n> ");
        read_line(line, sizeof(line));

        if (strcmp(line, "1") == 0) {
            buf = do_alloc();
        } else if (strcmp(line, "2") == 0) {
            do_print(buf);
        } else if (strcmp(line, "3") == 0) {
            do_free(buf);
        } else if (strcmp(line, "4") == 0) {
            load_flag();
        } else {
            puts("Bye!");
            return EXIT_SUCCESS;
        }
    }
}
