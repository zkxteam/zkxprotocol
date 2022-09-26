for file in ./
do
    for i in *.cairo; 
        do cairo-migrate "$i" -i; 
    done
done