#!/bin/sh
echo Download Physionet MMIDB
echo Download https://physionet.org/files/eegmmidb/1.0.0/
mkdir -p ./data/mmidb/
cd ./data/mmidb/
wget -r -N -c -np https://physionet.org/files/eegmmidb/1.0.0/

echo Download BCI Competition IV 2a
echo Download url https://www.bbci.de/competition/download/competition_iv/BCICIV_2a_gdf.zip
cd ..
cd ..
mkdir -p ./data/bci_iv_2a
cd ./data/bci_iv_2a
wget https://www.bbci.de/competition/download/competition_iv/BCICIV_2a_gdf.zip
unzip BCICIV_2a_gdf.zip

echo Download Kaggle ERN Competition
echo Download from https://www.kaggle.com/competitions/inria-bci-challenge/data
echo 
cd ..
cd ..
mkdir -p ./data/ern
cd ./data/ern
kaggle competitions download -c inria-bci-challenge
unzip inria-bci-challenge.zip
unzip test.zip
unzip train.zip

echo Download Sleep EDFx Cassette
echo Download from https://physionet.org/files/sleep-edfx/1.0.0/sleep-cassette/
cd ..
cd ..
mkdir -p ./data/sleep-edf/
cd ./data/sleep-edf/
wget -r -N -c -np https://physionet.org/files/sleep-edfx/1.0.0/sleep-cassette/

echo Download ERPBCI
echo Download from https://physionet.org/content/erpbci/1.0.0/
cd ..
cd ..
mkdir -p ./data/erpbci
cd ./data/erpbci/
wget -r -N -c -np https://physionet.org/files/erpbci/1.0.0/
