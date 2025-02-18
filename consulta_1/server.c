#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <pthread.h>

// This code implements a TCP/IP server that accepts messages containing integers.
// Each message represents the number of kilometers traveled by a truck in a month.
// The server sums these values into a variable called total_km, which tracks the
// total number of kilometers traveled by all trucks in the company.

// Please type here the correct port number before building:
#define PORT 12345 // It is recommended to edit the port number.

// Defining maximum number of waiting for connection clients.
#define MAX_CLIENTS 10 // Maximum number of clients in the waiting queue.

// Defining variables
unsigned long long total_km = 0; // Variable storing the total sum of kilometers driven by the trucks
// Total KMs is of type unsigned long long (min. 64 bits). A 32 bits integer would not be enough to store more than a year of data.
pthread_mutex_t lock; // Mutex to grant mutual exclusion when manipulating total_km var.
int current_connections = 0; // Variable that stores statistical infos.
int max_connections = 0; // Variable that stores statistical infos.
unsigned long long message_count = 0; // Variable that stores statistical infos.

void *handle_client(void *arg) {
    int ns = *(int *)arg;
    free(arg);
    char buffer[32];
    int bytes_received;

    // This piece of code has debugging and statistical purposes.
    // It's scope is to calculate the maximum number of concurrent connections.
    pthread_mutex_lock(&lock);
    current_connections++;
    if (current_connections > max_connections) {
        max_connections = current_connections;
    }
    pthread_mutex_unlock(&lock);

    // Checking if the TCP packet contains a message.
    while ((bytes_received = recv(ns, buffer, sizeof(buffer) - 1, 0)) > 0) {
        buffer[bytes_received] = '\0'; // Adds termination to buffer.
        unsigned int km = atoi(buffer); // From string to int.
        if (km < 0 || km > 16000) {
            // Checking if the kms are in a valid range. The client must send a message again if it receives a "Corrupted message" text.
            send(ns, "Corrupted message\n", 18, 0);
        } else {
            pthread_mutex_lock(&lock);   // Locking the mutex to guarantee mutual exclusion when manipulating total_km.
            total_km += km;              // It's absolutely necessary to prevent race conditions to maintain integrity.
            message_count++;             // Statstics&Debug.
            pthread_mutex_unlock(&lock); // The mutex is no longer needed.

            printf("Total KMs: %llu - KM received: %i - Message received: %s - Total messages: %llu\n", total_km, km, buffer, message_count);
            send(ns, "KM received\n", 12, 0); // Sending the client a confirmation that the KMs have been correctly received and registered.
        }
    }

    // Printing error if the packet doesn't contain a message.
    if (bytes_received < 0) {
        fprintf(stderr, "Error in recv\n");
    }

    // statistis&debug.
    pthread_mutex_lock(&lock);
    current_connections--;
    pthread_mutex_unlock(&lock);

    // Closing the connection.
    close(ns);
    return NULL;
}

// Function for debugging and statistics.
void *print_max_connections(void *arg) {
    while (1) {
        sleep(5);
        pthread_mutex_lock(&lock);
        printf("Max simultaneous connections: %d\n", max_connections);
        pthread_mutex_unlock(&lock);
    }
    return NULL;
}

int main() {
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);

    pthread_mutex_init(&lock, NULL); // Initializing the mutex.

    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
        perror("setsockopt failed");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind failed");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, MAX_CLIENTS) < 0) {
        perror("listen failed");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    printf("Server listening on port %d\n", PORT);

    pthread_t print_thread;
    pthread_create(&print_thread, NULL, print_max_connections, NULL);
    pthread_detach(print_thread);

    // Main loop that checks for new connections.
    while (1) {
        new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t *)&addrlen);
        if (new_socket < 0) {
            perror("accept failed");
            continue;
        }
        // Creating a new thread for every new socket connected,
        // in order to manage many clients at the same time.
        pthread_t thread_id;
        int *client_sock = (int *)malloc(sizeof(int));
        *client_sock = new_socket;
        pthread_create(&thread_id, NULL, handle_client, (void *)client_sock);
        pthread_detach(thread_id);
    }

    pthread_mutex_destroy(&lock);
    close(server_fd);
    return 0;
}