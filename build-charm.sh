#!/bin/bash

for path in ./*/; do
    [ -d "${path}" ] || continue # if not a directory, skip
    dirname="$(basename "${path}")"
    if [[ -d "$dirname/charms/native-charm" ]] ; then
        cd $dirname/charms/native-charm
        if charmcraft build ; then
            find ./ -mindepth 1 ! -regex '^./build\(/.*\)?' -delete
            cp -r ./build/* ./
            rm -rf ./build
        else
            echo "charmcraft build failed. The charm source code may not be present!"
        fi
        cd ../../..
        osm package-build $dirname
    fi
done

