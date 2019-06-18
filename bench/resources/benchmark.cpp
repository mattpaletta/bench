#include <string>
#include <iostream>

bool is_prime(long num) {
    int count = 0;
    // Naive way to determine if number is prime
    if (num == 0) {
        return false;
    } else {
        for (int i=2; i < num; i++) {
            if (num % i == 0) {
                count++;
            }
            if (count > 0) {
                return false;
            }
        }
    }

    return true;
}

void run_test() {
    std::cout << "Starting test" << std::endl;
	for (int i = 0; i < 100; i++) {
		is_prime(179425453 + i);
	}
	std::cout << "Done" << std::endl;
}

int main() {
    run_test();
}