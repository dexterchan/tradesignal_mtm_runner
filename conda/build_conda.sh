#rm -Rf conda-out/*
	conda build --output-folder ./conda-out/ ./conda/
	conda build purge
	upload_file=$(find conda-out -name "*.tar.bz2")
	
	upload_osx_64=$(find conda-out -name "*.tar.bz2" | grep osx)
	anaconda upload --force ${upload_osx_64}

	conda convert --platform linux-64 ${upload_file} -o ./conda-out
	upload_linux_64=$(find conda-out -name "*.tar.bz2" | grep linux-64)
	anaconda upload --force ${upload_linux_64}
	
    conda convert --platform linux-aarch64 ${upload_file} -o ./conda-out
    upload_linux_aarch64=$(find conda-out -name "*.tar.bz2" | grep linux-aarch64)
	anaconda upload --force ${upload_linux_aarch64}

