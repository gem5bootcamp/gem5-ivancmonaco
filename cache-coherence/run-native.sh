for((i=1; i <= $3; i++)); do
    ./workloads/array_sum/$1-native 32768 $2 | tail -n 1 >> results/$1-native-$2.txt
done
