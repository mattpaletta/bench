package main

import (
	"sync"
	"math/rand"
	"time"
	"os"
	"strconv"
	"fmt"
)

func random(n int) []int {
	s := make([]int, n)

	src := rand.NewSource(time.Now().UnixNano())
	rand := rand.New(src)

	for i := 0; i < n; i ++ {
		s[i] = rand.Intn(n)
	}

	return s
}

const max = 1 << 11

func merge(s []int, middle int) {
	helper := make([]int, len(s))
	copy(helper, s)

	helperLeft := 0
	helperRight := middle
	current := 0
	high := len(s) - 1

	for helperLeft <= middle-1 && helperRight <= high {
		if helper[helperLeft] <= helper[helperRight] {
			s[current] = helper[helperLeft]
			helperLeft++
		} else {
			s[current] = helper[helperRight]
			helperRight++
		}
		current++
	}

	for helperLeft <= middle-1 {
		s[current] = helper[helperLeft]
		current++
		helperLeft++
	}
}

/* Sequential */
func mergesort(s []int) {
	if len(s) > 1 {
		middle := len(s) / 2
		mergesort(s[:middle])
		mergesort(s[middle:])
		merge(s, middle)
	}
}

/* Parallel 3 */
func parallelMergesort3(s []int) {
	len := len(s)

	if len > 1 {
		middle := len / 2

		var wg sync.WaitGroup
		wg.Add(2)

		go func() {
			defer wg.Done()
			parallelMergesort3(s[:middle])
		}()

		go func() {
			defer wg.Done()
			parallelMergesort3(s[middle:])
		}()

		wg.Wait()
		merge(s, middle)
	}
}

func main() {
    argsWithoutProg := os.Args[1:]
    num_length, err := strconv.Atoi(argsWithoutProg[1])
    if err != nil {
		fmt.Println(err)
		return;
	}

	my_list := random(num_length)

    parallelMergesort3(my_list)
}