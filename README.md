
## Amazon VOD Preset Converter

Python script that allows users to convert Amazon Elastic Transcoder presets to AWS Elemental MediaConvert presets.

###  Setting up Environment 
You will need to install Python 2.7 onto the machine where you are running the script

#### Verify Python is Installed

Python may be installed by default on your machine, or you may have used it in a previous workflow.
To verify if Python is installed and what version you have, run the following command:
```
python –version
```
Please make sure that the Python version is a variation of **2.7.x**. 

#### Installing AWS CLI

Use the following URL for the latest “Installing the AWS Command Line Interface”

[http://docs.aws.amazon.com/cli/latest/userguide/installing.html](http://docs.aws.amazon.com/cli/latest/userguide/installing.html)

```
$ aws configure
AWS Access Key ID [****************1234]:
AWS Secret Access Key [****************abc]:
Default region name [us-east-1]:
Default output format [json]: json
```

#### Pre-Work

Make sure the ets_mediaconvert_preset_v2.py is located on your machine, and then make ets_medaconvert_preset_v2.py executable using the following chmod command:
```
chmod +x ets_mediaconvert_preset_v2.py
```

###  Script Parameters
Running the script will provide the following help menu. You can also use the ‘-h’ parameter to show the help menu.

```
$ python ets_mediaconvert_preset_v2.py
usage: ets_mediaconvert_preset_v2.py [-h] [-r REGION] [-p ETSID] [-v] [-i] [-c OUTPUTTYPE] [-f]
ETS to AWS Elemental MediaConvert preset converter

optional arguments:
-h, --help                               show this help message and exit
-r REGION, --aws-region REGION           Valid ETS AWS Region to connect to
-p ETSID, --preset-id                    ETSID ETS Preset ID
-v, --verbose                            Verbose debug messages
-i, --interactive                        Interactive Mode for user
-c OUTPUTTYPE, --output-type OUTPUTTYPE  Output group type for preset to move to 
                                         ex: file, apple, dash, smooth
-f, --save                               Save presets to file
```


The following parameters are required if you are not using interactive mode.

-r, -p, -c

If you use interactive mode (‘-i’) then all other parameters fed in will be ignored and you will need to follow the prompts.

If you want verbose logging enabled, use the ‘-v’ parameter. When verbose logging is enabled, you will see the JSON output for each step of the conversion process.

For the ETS Preset ID (-p, --preset-id), you can find a list of your presets by logging into the AWS Console, selecting Amazon Elastic Transcoder from the services menu, and clicking on Presets in the left hand navigation.

####  Error Handling

The script handles improper configurations and warns the user when this happens.

Error examples:

1. Containers and Codecs not currently supported by AWS Elemental MediaConvert
2. Improper output group configurations, such as DASH with Transport Stream codecs

#### Saving Preset to File

When using the -f (or --save) flag this will save two files. One contains the video and audio parameters the other contains a Thumbnail preset. When this flag is excluded, the output of the script will just print on the terminal screen.

## License

This library is licensed under the Apache 2.0 License.
