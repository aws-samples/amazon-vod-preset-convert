# ---------------------------------------------------------------------------
# Amazon ElasticTranscoder to AWS Elemental MediaConvert preset converter. 
# Version: 2.1
#
# 2.1
#   - Added Thumbnail preset creationg
#   - Added -f option to save preset and thumbnail preset to files
#   - Corrected interlaced mode 
#   - Corrected Codec Level logic
#
# 2.2
#    -Corrected Auto logic for video/frame capture resolution, sample rate, and bitate
#    -Validation for audio only on MP4 only outputs
# 
# 2.3
#    -Corrected casting logic
#    -added fMP4 support for dash and smooth outputs
#    -added more validation around container conversion types
#    -updated supported AAC range 
#
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# ---------------------------------------------------------------------------


import hashlib
import json
import boto.elastictranscoder
import datetime
import time
import hashlib
import json
import os
import boto3
from botocore.exceptions import ClientError

import argparse

#Options###
parser = argparse.ArgumentParser(prog='ets_mediaconvert_preset_v2.py',description='ETS to AWS Elemental MediaConvert preset converter',add_help=True)
parser.add_argument('-r', '--aws-region', action='store', dest='region', help='Valid ETS AWS Region to connect to')
parser.add_argument('-p', '--preset-id', action='store', dest='etsid', help='ETS Preset ID')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose debug messages')
#arser.add_argument('-l','--preset-list',action='store',dest='listpresets',help='Feed list of presets ID into script')
parser.add_argument('-i', '--interactive', action='store_true', help='Interactive Mode for user')
parser.add_argument('-c', '--output-type', action='store', dest='outputtype', help='Output group type for preset to move to ex: file, apple, dash, smooth')
parser.add_argument('-f', '--save', action='store_true', help='Save presets to file')
args = parser.parse_args()

##Print help if no args
if (args.interactive==False and (args.region==None or args.etsid==None or args.outputtype==None)):
    parser.print_help()
    exit()

outputtype=['file','apple','dash','smooth']
unsupport_container = ['"webm"','"mp3"','"ogg"','"flac"','"flv"','"gif"']
unsupport_video_codec = ['"vp8"','"vp9"','"gif"']
unsupport_audio_codec = ['"vorbis"','"flac"','"wav"']



###Check region support

def validation_region():

    if args.interactive==False:
        while True:
            region = args.region.lower()
            if (region == 'us-east-1') or (region == 'us-west-1') or (region == 'us-west-2') or (region == 'eu-west-1') or (region == 'ap-southeast-1') or (region == 'ap-southeast-2') or (region == 'ap-south-1') or (region == 'ap-northeast-1'):
                return region
            else:
                print("Unsupported region selected..exiting")
                exit()
    else: 
        while True:
            region = raw_input("Please type in a supported ETS region: ").lower() 
            if (region.strip() == 'us-east-1') or (region.strip() == 'us-west-1') or (region.strip() == 'us-west-2') or (region.strip() == 'eu-west-1') or (region.strip() == 'ap-southeast-1') or (region.strip() == 'ap-southeast-2') or (region.strip() == 'ap-south-1') or (region.strip() == 'ap-northeast-1'):
                return region
                break

def validation_preset():
    if args.interactive==False:
        while True:
            try:
               etspresetid = args.etsid.lower()
               read_preset_result = etsclient.read_preset(etspresetid)
               return etspresetid, read_preset_result
            except Exception as e:
                print e
                exit()
    else:
        while True:

            presetid = raw_input("Preset ID: ").lower()
            try:
               read_preset_result = etsclient.read_preset(presetid)
               return presetid, read_preset_result
            except Exception as e:
                print e
                print "Please enter a correct preset id"


def validate_container(ets_preset_payload, unsupported):
    if  json.dumps(ets_preset_payload['Preset']['Container']) in unsupported:
        print 'Unsupported Container found in preset, please try another preset'
        exit()
    else:
        supported_container = json.dumps(ets_preset_payload['Preset']['Container'])
        if args.verbose == True: 
            print '==================VERBOSE LOGGING=================='
            print 'Supported Container Found!'
            print supported_container
        return supported_container

def validate_video(ets_preset_payload, unsupported):
    
	if ets_preset_payload['Preset']['Video']:
    		if  json.dumps(ets_preset_payload['Preset']['Video']['Codec']) in unsupported:
        		print 'Unsupported Video codec found in preset, please try anohter preset'
        		exit()
    		else:
        		supported_video = json.dumps(ets_preset_payload['Preset']['Video']['Codec'])
        		if args.verbose == True:
            			print '==================VERBOSE LOGGING=================='
            			print 'Supported Video Codec Found!'
            			print  supported_video
        		return supported_video  
	else:
		supported_video = 'none'
		return supported_video


def validate_audio(ets_preset_payload, unsupported):
	if ets_preset_payload['Preset']['Audio']:
    		if  json.dumps(ets_preset_payload['Preset']['Audio']['Codec']) in unsupported:
        		print 'Unsupported Video condec found in preset, please try anohter preset'
        		exit()
    		else:
        		supported_audio = json.dumps(ets_preset_payload['Preset']['Audio']['Codec'])
        		if args.verbose == True:
            			print '==================VERBOSE LOGGING=================='
            			print 'Supported Audio Codec Found'
            			print supported_audio
        		return supported_audio
	else:
		supported_audio = 'none'
		return supported_audio

def validate_output(outputtype):
    if args.interactive==True:
        while True:
            emf_outputgroup = raw_input("Please type in output a output group type you want to place this ETS preset into, options are file, apple, dash, smooth: ")
            if emf_outputgroup.lower() in outputtype: 
                return emf_outputgroup
    else:
        if args.outputtype.lower() in outputtype:
            emf_outputgroup = args.outputtype
            return emf_outputgroup
        else:
            print "Output group type must be file, apple, dash, or smooth"
            exit()

def translate_audio(ets_preset_payload,s_audio):
    audiodump = json.dumps(ets_preset_payload['Preset']['Audio'])
    ets_channel_num = json.dumps(ets_preset_payload['Preset']['Audio']['Channels'])
    if ets_channel_num == '"auto"':
        ets_channel_num = '"2"'
    else: 
        ets_channel_num = json.dumps(ets_preset_payload['Preset']['Audio']['Channels'])

    ets_audio_bitrate = int(json.dumps(ets_preset_payload['Preset']['Audio']['BitRate']).strip('"'))
   
    
    ets_audio_sample = json.dumps(ets_preset_payload['Preset']['Audio']['SampleRate']).strip('"')
    
    if ets_audio_sample == "auto":
        ets_audio_sample = 48
    else:
        ets_audio_sample = long(json.dumps(ets_preset_payload['Preset']['Audio']['SampleRate']).strip('"'))
    ###Translate Audio Profile###
    ###AAC Type
    if s_audio == '"AAC"':
        etsaudioprofile = json.dumps(ets_preset_payload['Preset']['Audio']['CodecOptions']['Profile'])
        aac_range=[64,84,96,112,128,192,224,256,288,320,384,448,512,576]
        if etsaudioprofile == '"AAC-LC"':
            audio_profile = 'LC'
        elif etsaudioprofile == '"HE-AAC"':
            audio_profile = 'HEV1'
        elif etsaudioprofile ==  '"HE-AACV2"':
            audio_profile = 'HEV2'
        else:
            audio_profile = 'LC'
            print "Warning: No matching profile found, changing to lc \n"
        
        if ets_channel_num == '"2"':
            audio_coding = "CODING_MODE_2_0"
        elif ets_channel_num == '"1"':
            audio_coding == "CODING_MODE_1_0"
        else:
            audio_coding == "CODING_MODE_2_0"
        
        emf_bitrate = str(min(aac_range, key=lambda x:abs(x-ets_audio_bitrate)))       
        emf_bitrate = long(emf_bitrate) * 1000 
	emf_sample = ets_preset_payload['Preset']['Audio']['SampleRate']
        AudioSettings = {}
        AudioSettings = {
                 "LanguageCodeControl": "FOLLOW_INPUT",
                 "AudioTypeControl": "FOLLOW_INPUT",
                 "AudioSourceName": "Audio Selector 1",
                 'CodecSettings':{
                 'Codec': 'AAC',       
                 'AacSettings': {
                 'AudioDescriptionBroadcasterMix': "NORMAL",
                 'Bitrate': emf_bitrate,
                 'CodecProfile': audio_profile,
                 'CodingMode': audio_coding,
                 'RawFormat': "NONE",
                 'Specification': "MPEG4",
                 'RateControlMode': 'CBR',
        }}}
        

        if emf_sample != 'auto':
             AudioSettings['CodecSettings']['AacSettings'].update({"SampleRate": int(emf_sample)})
        else:
 	     warning = "Auto in setting Sample Rate not supported...defaulting to  48kHz\n"
             AudioSettings['CodecSettings']['AacSettings'].update({"SampleRate": int(48000)})


        if args.verbose == True:
            print '==================VERBOSE LOGGING=================='
            print '==================AUDIO SETTINGS AAC=================='
            print json.dumps(AudioSettings)
    
    ###PCM/WAV Type
    elif s_audio == '"wav"' or s_audio == '"pcm"':
        wav_sample=[8,16,22.05,24,32,44.1,48,88.2,96,192] 
        emf_sample = str(min(wav_sample, key=lambda x:abs(x-ets_audio_sample)))
        emf_sample = int(emf_sample) * 1000
	ets_bitdepth=[16,24]

        emf_bitdepth=str(min(ets_bitdepth, key=lambda x:abs(x-int(json.dumps(ets_preset_payload['Preset']['Audio']['CodecOptions']['BitDepth']).strip('"')))))
        

        if json.dumps(ets_preset_payload['Preset']['Audio']['Channels']) == '"auto"' or json.dumps(ets_preset_payload['Preset']['Audio']['Channels'])== '"0"':
            warning = "0 and auto channels not supported...defaulting to 2\n"
            emf_channels = "2"
        else:
            emf_channels = json.dumps(ets_preset_payload['Preset']['Audio']['Channels']).strip('"')


        AudioSettings = {}
        AudioSettings = {
                    "LanguageCodeControl": "FOLLOW_INPUT",
                    "AudioTypeControl": "FOLLOW_INPUT",
                    "AudioSourceName": "Audio Selector 1",
		    'CodecSettings':{
                    'Codec': 'WAV',
                    'WavSettings': {
                    'BitDepth': int(emf_bitdepth),
                    'Channels': int(emf_channels),
                    }}}

        if emf_sample != 'auto':
                AudioSettings['CodecSettings']['WavSettings'].update({"SampleRate": int(emf_sample)})
        else:
                warning = "Auto in setting Sample Rate not supported...defaulting to 44.1kHz\n"
                AudioSettings['CodecSettings']['WavSettings'].update({"SampleRate": int(44100)})
        if args.verbose == True:
            print '==================VERBOSE LOGGING=================='
            print '==================AUDIO SETTINGS WAV=================='
            print json.dumps(AudioSettings)
        

    ###Type MP2
    elif s_audio == '"mp2"':
        mp2_range = [32,48,56,64,80,96,112,128,160,192,224,256,320,384]
        mp2_sample_range =[32,44.1,48]
        
        emf_bitrate = min(mp2_range, key=lambda x:abs(x-ets_audio_bitrate))
        emf_sample = min(mp2_sample_range, key=lambda x:abs(x-ets_audio_sample))
        emf_bitrate = str(min(mp2_range, key=lambda x:abs(x-ets_audio_bitrate)))
        emf_bitrate = int(emf_bitrate) * 1000
	emf_sample = emf_sample * 1000
        AudioSettings = {}

        if json.dumps(ets_preset_payload['Preset']['Audio']['Channels']) == '"auto"' or json.dumps(ets_preset_payload['Preset']['Audio']['Channels'])== '"0"':
            print "Warning = 0 and auto channels not supported...defaulting to 2\n"
            emf_channels = "2"
        else:
            emf_channels = json.dumps(ets_preset_payload['Preset']['Audio']['Channels']).strip('"') 
        AudioSettings = {
                    "LanguageCodeControl": "FOLLOW_INPUT",
                    "AudioTypeControl": "FOLLOW_INPUT",
		    "AudioSourceName": "Audio Selector 1",
                    'CodecSettings':{
                    'Codec': 'MP2',
                    'Mp2Settings': {
                    'Bitrate': int(emf_bitrate),
                    'Channels': int(emf_channels),
                    }}}
        if args.verbose == True:
            print '==================VERBOSE LOGGING=================='
            print '==================AUDIO SETTINGS MP2=================='
            print json.dumps(AudioSettings)
   
        if emf_sample != 'auto':
                AudioSettings['CodecSettings']['Mp2Settings'].update({"SampleRate": int(emf_sample)})
        else:
                warning = "Auto in setting Sample Rate not supported...defaulting to 48000kHz\n"
                AudioSettings['CodecSettings']['Mp2Settings'].update({"SampleRate": int(48000)})

    AudioDescription = {}
    AudioDesc1 = {}
    AudioDesc1 = {"LanguageCodeControl": "FOLLOW_INPUT",
                 "InputTypeControl": "FOLLOW_INPUT",
                  "AudioSourceName": "Audio Selector 1",}  
 
    AudioExtra = json.dumps(AudioDesc1, indent=4,sort_keys=True)
    
    AudioDescription ={
    "AudioDescriptions":[
    ]}
    
    AudioDescription['AudioDescriptions'].insert(0, AudioSettings) 

    if args.verbose == True:
        print '==================VERBOSE LOGGING=================='    
        print '==================AUDIO DESCRIPTION=================='
        print json.dumps(AudioDescription,indent=4, sort_keys=True)
    return AudioDescription

 

def translate_video(ets_preset_payload, s_video):
    
    ##Checks for Profile for h264 - not putting into fill h264 if due to if ets support h265 in future will be easier to migrate 

    videodump = json.dumps(ets_preset_payload['Preset']['Video'])
    if 'Profile' in videodump and s_video != '"mpeg2"':
        emf_codec_profile = ets_preset_payload['Preset']['Video']['CodecOptions']['Profile'].upper()
        emf_codec_level = ets_preset_payload['Preset']['Video']['CodecOptions']['Level']
        
        cavlc_profile =  ["HIGH","HIGH_10BIT","HIGH_422","HIGH_422_10BIT","MAIN","BASELINE"]
        if emf_codec_profile in cavlc_profile :
              emf_entropy_encoding = "CAVLC"
        else:
             emf_entropy_encoding = "CABAC"
 
        ##Logic for Level 1b that isn't supported in AWS Elemental MediaConvert
        if emf_codec_level == '"1b"':
            emf_codec_level = '"AUTO"'
            print "WARNING: 1b not supported in AWS Elemental MediaConvert, defaulting to auto, please change to 1 or 1.1 based off bitrate and resolution \n"
        else:
            emf_codec_level = ets_preset_payload['Preset']['Video']['CodecOptions']['Level']
	if emf_codec_level == '1':
		emf_codec_level = 'LEVEL_1'		
	elif emf_codec_level == '1.1':
		emf_codec_level = 'LEVEL_1_1'
	elif emf_codec_level == '1.2':
		emf_codec_level = 'LEVEL_1_2'
	elif emf_codec_level == '1.3':
		emf_codec_level = '"LEVEL_1_3"'  
	elif emf_codec_level == '2':
		emf_codec_level = 'LEVEL_2'
	elif emf_codec_level == '2.1':
		emf_codec_level = 'LEVEL_2_1'
	elif emf_codec_level == '2.2':
		emf_codec_level = 'LEVEL_2_2'
	elif emf_codec_level == '3':
		emf_codec_level = 'LEVEL_3'
	elif emf_codec_level == '3.1':
		emf_codec_level = 'LEVEL_3_1'
	elif emf_codec_level == '3.2':
		emf_codec_level = 'LEVEL_3_2' 
	elif emf_codec_level == '4':
		emf_codec_level = 'LEVEL_4'
	elif emf_codec_level == '4.1':
		emf_codec_level = 'LEVEL_4_1'
	else:
	    emf_codec_level = "AUTO"
            print "WARNING: Item not found defaulting to auto, please change based off bitrate and resolution \n"
    
    if (ets_preset_payload['Preset']['Video']['MaxWidth'] == 'auto') or (ets_preset_payload['Preset']['Video']['MaxHeight'] == 'auto'):
        emf_codec_level = "AUTO"
        print "WARNING: Since resolution is not defined setting Profile Level to AUTO"
    
    ## Interlace Mode Logic

    if ets_preset_payload['Preset']['Video']['CodecOptions']['InterlacedMode'] == 'Progressive':
        emf_interlace_mode = 'PROGRESSIVE'
    elif ets_preset_payload['Preset']['Video']['CodecOptions']['InterlacedMode'] == 'TopFirst':
        emf_interlace_mode = 'TOP_FIELD'
    elif ets_preset_payload['Preset']['Video']['CodecOptions']['InterlacedMode'] == 'BottomFirst':
        emf_interlace_mode = 'BOTTOM_FIELD'
    elif ets_preset_payload['Preset']['Video']['CodecOptions']['InterlacedMode'] == 'Auto':
        emf_interlace_mode = 'PROGRESSIVE'
	print "WARNING: Auto interlaced mode not supported in MediaConvert, setting to progressive";
    else:
        emf_interlace_mode = 'PROGRESSIVE'
    
    ###Strech output###
    if ets_preset_payload['Preset']['Video']['SizingPolicy'] == '"Stretch"':
        emf_stretch = "STRETCH_TO_OUTPUT"
    else:
        emf_stretch = "DEFAULT"

    ###ColorsSpace Conversion Precessor
    if ets_preset_payload['Preset']['Video']['CodecOptions']['ColorSpaceConversionMode'] == "None":
        emf_enable_color = False
    elif ets_preset_payload['Preset']['Video']['CodecOptions']['ColorSpaceConversionMode'] == "Bt601ToBt709":
        emf_enable_color = True
        emf_color_space_conversion =  'FORCE_709'
    elif ets_preset_payload['Preset']['Video']['CodecOptions']['ColorSpaceConversionMode'] == "Bt709ToBt601":
        emf_enable_color = True
        emf_color_space_conversion = 'FORCE_601'
    else:
        emf_enable_color = False
        print "WARNING: Auto in ColorSpaceConversion is not supported in EMF setting ColorSpace on input to Auto and disabling color correction\n"

    if s_video == '"H.264"':
        xSettings = 'H264Settings'
        VideoSettings = {}
        VideoSettings ={'Codec': 'H_264',
                    'H264Settings': {
                    'AdaptiveQuantization': 'HIGH',
                    'HrdBufferInitialFillPercentage': 90,
                    'CodecLevel': emf_codec_level,
                    'CodecProfile': emf_codec_profile,
                    'FlickerAdaptiveQuantization': "ENABLED",
                    'EntropyEncoding': emf_entropy_encoding,
                    'GopBReference': "DISABLED",
                    'GopClosedCadence': 1,
                    'NumberBFramesBetweenReferenceFrames': 0,
                    'GopSize': int(ets_preset_payload['Preset']['Video']['KeyframesMaxDist']),
                    'GopSizeUnits': 'FRAMES',
                    'InterlaceMode': emf_interlace_mode,
                    'FramerateConversionAlgorithm': "DUPLICATE_DROP",
                    'MinIInterval': 0,
                    'NumberReferenceFrames': int(ets_preset_payload['Preset']['Video']['CodecOptions']['MaxReferenceFrames']),
                    'QualityTuningLevel': "SINGLE_PASS",
                    'RepeatPps': "DISABLED",
                    'Syntax': "DEFAULT",
                    'SceneChangeDetect': "ENABLED",
                    'UnregisteredSeiTimecode': "DISABLED",
                    'Slices': 1,
                    'FlickerAdaptiveQuantization': "DISABLED",
                    'SlowPal': "DISABLED",
                    'Softness': 0,
                    'SpatialAdaptiveQuantization': "ENABLED",
                    'Telecine': 'NONE',
                    'TemporalAdaptiveQuantization': "ENABLED"},    
                     }
       

    elif s_video == '"mpeg2"':
        xSettings = 'Mpeg2Settings'
        VideoSettings = {}

        VideoSettings ={'Codec': 'MPEG2',
                    'Mpeg2Settings': {
                    'CodecLevel': 'AUTO',
                    'CodecProfile': 'MAIN',
                    'GopClosedCadence': 1,
                    'NumberBFramesBetweenReferenceFrames': 2,
                    'GopSize': int(ets_preset_payload['Preset']['Video']['KeyframesMaxDist']),
                    'GopSizeUnits': 'FRAMES',
                    'InterlaceMode': emf_interlace_mode,
                    'FramerateConversionAlgorithm': "DUPLICATE_DROP",
                    'MinIInterval': 0,
                    'QualityTuningLevel': "SINGLE_PASS",
                    'SceneChangeDetect': "ENABLED",
                    'SlowPal': "DISABLED",
                    'Softness': 0,
                    'SpatialAdaptiveQuantization': "ENABLED",
                    'Telecine': 'NONE',
                    'TemporalAdaptiveQuantization': "ENABLED"}
                  }

    
    VideoDescription = {}
    
    VideoDescription ={
    "VideoDescription": {
            "TimecodeInsertion": "DISABLED" ,
            "AntiAlias": "ENABLED",
            "Sharpness": 100,
            "AfdSignaling": "NONE",
            "RespondToAfd": "NONE",
            "ColorMetadata": "INSERT",
            "ScalingBehavior": emf_stretch,
            "CodecSettings": {
            }}}
    if emf_enable_color:
        VideoPreProcessors ={}
        VideoPreProcessors={
        'VideoPreprocessors': {
                'ColorCorrector': {
                'Brightness': 50,
                'ColorSpaceConversion': emf_color_space_conversion,
                'Contrast': 50,
                'Hue': 0,
                'Saturation': 0 
                }}}
        VideoDescription['VideoDescription'].update(VideoPreProcessors)
   
    ##Handle Auto Resolution
    if ets_preset_payload['Preset']['Video']['MaxWidth'] != 'auto':
        VideoDescription['VideoDescription'].update({"Width" : int(ets_preset_payload['Preset']['Video']['MaxWidth'])})

    if ets_preset_payload['Preset']['Video']['MaxHeight'] != 'auto':
        VideoDescription['VideoDescription'].update({"Height" : int(ets_preset_payload['Preset']['Video']['MaxHeight'])})

    ########################################
    #                                      #
    #         All Codec Type Items         #
    #                                      #
    ########################################
    

    
    ###ETS FrameRate auto to EMF FrameRate Follow
    if ets_preset_payload['Preset']['Video']['FrameRate'] == 'auto':
        emf_codec_framerate = "Follow"
        emf_framerate = "INITIALIZE_FROM_SOURCE"
        VideoSettings[xSettings].update({'FramerateControl': emf_framerate})
        

    else:
        emf_codec_framerate = ets_preset_payload['Preset']['Video']['FrameRate']
        emf_framerate = "SPECIFIED"
        VideoSettings[xSettings].update({'FramerateControl': emf_framerate})
        
        ###Logic for FrameRate Fraction
        if float(emf_codec_framerate).is_integer() :
            VideoSettings[xSettings].update({'FramerateDenominator': 1})
            VideoSettings[xSettings].update({'FramerateNumerator': int(emf_codec_framerate)})        
        else:
            VideoSettings[xSettings].update({'FramerateDenominator': 1001})
            if emf_codec_framerate == "29.97" :
            	emf_codec_framerate = 30000
            elif emf_codec_framerate == "23.97":
		emf_codec_framerate = 24000
            
	    VideoSettings[xSettings].update({'FramerateNumerator': emf_codec_framerate})

    ###Logic for PAR
    if ets_preset_payload['Preset']['Video']['DisplayAspectRatio'] == "auto":            
        emf_codec_par = "Follow"
        emf_par = "INITIALIZE_FROM_SOURCE"    
        VideoSettings[xSettings].update({'ParControl': emf_par})
        
    elif ets_preset_payload['Preset']['Video']['DisplayAspectRatio'] == "1:1":
        emf_codec_par_num = 1
        emf_codec_par_dem = 1
        VideoSettings[xSettings].update({'ParNumerator': emf_codec_par_num})
        VideoSettings[xSettings].update({'ParDenominator': emf_codec_par_dem}) 
        emf_par = "SPECIFIED"
        VideoSettings[xSettings].update({'ParControl': emf_par})

    elif ets_preset_payload['Preset']['Video']['DisplayAspectRatio'] == "4:3":
    
        par_num = 4 
        emf_codec_par_dem = 3
        VideoSettings[xSettings].update({'ParNumerator': emf_codec_par_num})
        VideoSettings[xSettings].update({'ParDenominator': emf_codec_par_dem})
        emf_par = "SPECIFIED"
        VideoSettings[xSettings].update({'ParControl': emf_par})

    elif ets_preset_payload['Preset']['Video']['DisplayAspectRatio'] == "3:2":

        par_num = 3
        emf_codec_par_dem = 2
        VideoSettings[xSettings].update({'ParNumerator': emf_codec_par_num})
        VideoSettings[xSettings].update({'ParDenominator': emf_codec_par_dem})
        emf_par = "SPECIFIED"
        VideoSettings[xSettings].update({'ParControl': emf_par})
    
    elif ets_preset_payload['Preset']['Video']['DisplayAspectRatio'] == "16:9":
        emf_codec_par_num = 40
        emf_codec_par_dem = 30
        VideoSettings[xSettings].update({'ParNumerator': emf_codec_par_num})
        VideoSettings[xSettings].update({'ParDenominator': emf_codec_par_dem})
        emf_par = "SPECIFIED"
        VideoSettings[xSettings].update({'ParControl': emf_par})
    ###Rate Control Modes/BitRate/Buffer
    
    if 'MaxBitrate' in videodump:
        if int(ets_preset_payload['Preset']['Video']['MaxBitRate']) > 0:
            emf_control_mode = 'VBR'
            VideoSettings[xSettings].update({'RateControlMode': emf_control_mode})
            emf_max_bitrate = int(ets_preset_payload['Preset']['Video']['MaxBitRate'])
            VideoSettings[xSettings].update({'MaxBitrate': emf_max_bitrate})
            if ets_preset_payload['Preset']['Video']['Bitrate'] == '"auto"':
                print "WARNING: auto not a supported bitrate parameter in EMF setting to default to 5M"
                emf_bitrate = 5000000
                VideoSettings[xSettings].update({'Bitrate': emf_bitrate})
            else:
                emf_bitrate = int(ets_preset_payload['Preset']['Video']['BitRate'])
                VideoSettings[xSettings].update({'Bitrate': emf_bitrate})
                emf_max_bitrate = int(ets_preset_payload['Preset']['Video']['MaxBitRate'])
                VideoSettings[xSettings].update({'MaxBitrate': emf_max_bitrate})
    else:
        emf_control_mode = 'CBR'
        if ets_preset_payload['Preset']['Video']['BitRate']  != 'auto':
            VideoSettings[xSettings].update({'RateControlMode': emf_control_mode})
            emf_bitrate_temp = int(ets_preset_payload['Preset']['Video']['BitRate'])
	    ##convert kilobits to bits
            emf_bitrate = emf_bitrate_temp * 1000   
	
	
	    if emf_bitrate < 1000:
		    print "WARNING: Bitrate must be greater than 1000, increase to 1000\n"
		    emf_bitrate = 1000
        else:
             emf_bitrate = 5000000
             VideoSettings[xSettings].update({'RateControlMode': emf_control_mode})
        VideoSettings[xSettings].update({'Bitrate': emf_bitrate})


    
        
    VideoDescription['VideoDescription'].update({'CodecSettings': VideoSettings})
    
    if args.verbose == True:
        print '==================VERBOSE LOGGING=================='
        print '==================VIDEO DESCRIPTION=================='
        print json.dumps(VideoDescription,indent=4, sort_keys=True)
    
    return VideoDescription  


def translate_container(emf_AudioDescription,emf_VideoDescription,s_container,emf_outputgroup,s_video):
	if emf_VideoDescription == 'none' and s_container != '"mp4"':
			print "Audio only is supported in MP4 contianers\n"
			exit();

	if emf_outputgroup == 'apple' and s_container == '"ts"':
        	OutputGroupSettings = {}
        	OutputGroupSettings ={
        	"Settings":{
        	"ContainerSettings": {
        	"Container": "M3U8",
        	"M3u8Settings": {
        	"AudioFramesPerPes": 2,
        	"PcrControl": "PCR_EVERY_PES_PACKET",
        	"PmtPid": 480,
        	"Scte35Source": "NONE",
        	"ProgramNumber": 1,
        	"PatInterval": 100,
        	"PmtInterval": 100,
        	"TimedMetadata": "NONE",
        	"VideoPid": 481,
        	"AudioPids": [482,483,484,485,486,487,488,489,490,491,492]
        	}}}}
		if emf_VideoDescription is not 'none':
			OutputGroupSettings['Settings'].update(emf_VideoDescription)
		if emf_AudioDescription is not 'none':
			OutputGroupSettings['Settings'].update(emf_AudioDescription)
		return OutputGroupSettings         
	elif emf_outputgroup == 'apple' and s_container == '"mp4"':
		print "This tool only supports converting Non-CMAF HLS presets"
		exit()
	elif emf_outputgroup == 'apple' and s_container is not '"ts"':
		print "ETS Preset must be in a ts container"
		exit()
    
	if emf_outputgroup == 'dash' and s_video == '"H.264"' and s_container == '"fmp4"':
		OutputGroupSettings = {}
		OutputGroupSettings ={        
		"Settings":{
		"ContainerSettings": {
		"Container": "mpd"
		}}}
		if emf_VideoDescription is not 'none':	
			OutputGroupSettings['Settings'].update(emf_VideoDescription)
		if emf_AudioDescription is not 'none':
			OutputGroupSettings['Settings'].update(emf_AudioDescription)
		return OutputGroupSettings
	elif emf_outputgroup == 'dash' and s_container is not '"fmp4"':
			print "ETS Preset must have container set to fmp4 for DASH conversion"
			exit()
  
	if emf_outputgroup == 'smooth' and s_video == '"H.264"' and s_container == '"fmp4"':
		OutputGroupSettings = {}
		OutputGroupSettings ={
		"Settings":{
		"ContainerSettings": {
		"Container": "ismv"
		}}}
		if emf_VideoDescription is not 'none':
			OutputGroupSettings['Settings'].update(emf_VideoDescription)
		if emf_AudioDescription is not 'none':
			OutputGroupSettings['Settings'].update(emf_AudioDescription)
		return OutputGroupSettings
	elif emf_outputgroup == 'smooth' and s_container is not '"fmp4"':
		print "ETS Preset must have contianer set to fmp4 for smooth conversion"
		exit()




	if emf_outputgroup == 'file':
		if s_container == '"ts"' or s_container == '"mpg"':
            		OutputGroupSettings = {}
            		OutputGroupSettings ={
            			"Settings":{
            			"ContainerSettings": {
            			"Container": "M2TS",
            			"M2tsSettings":{
            			"AudioBufferModel": "ATSC",
            			"EsRateInPes": "EXCLUDE",
            			"PatInterval": 100,
            			"Scte35Source": "NONE",
            			"VideoPid": 481,
            			"PmtInterval": 100,
            			"SegmentationStyle": "MAINTAIN_CADENCE",
            			"PmtPid": 480,
            			"Bitrate": 0,
            			"AudioPids": [482, 483,484,485, 486,487, 488, 489, 490,491, 492],
            			"PrivateMetadataPid": 503,
            			"DvbSubPids": [460,461,462,463,464,465,466,467,468,469,470,471,472,473,474,475, 476,477,478,479],
            			"RateMode": "CBR",
            			"AudioFramesPerPes": 2,
            			"PcrControl": "PCR_EVERY_PES_PACKET",
            			"SegmentationMarkers": "NONE",
            			"EbpAudioInterval": "VIDEO_INTERVAL",
            			"ProgramNumber": 1,
            			"BufferModel": "MULTIPLEX",
            			"DvbTeletextPid": 499,
            			"EbpPlacement": "VIDEO_AND_AUDIO_PIDS",
            			"NullPacketBitrate": 0
        			}}}}
			if emf_VideoDescription is not 'none':
            			OutputGroupSettings['Settings'].update(emf_VideoDescription)
        		if emf_AudioDescription is not 'none':
				OutputGroupSettings['Settings'].update(emf_AudioDescription)
        		return OutputGroupSettings

        	elif s_container == '"mp4"':
            		OutputGroupSettings = {}
           		OutputGroupSettings ={
            		"Settings":{
            		"ContainerSettings": {
            		"Container": "MP4",
            		"Mp4Settings": {
            		"CslgAtom": "INCLUDE" ,
            		"FreeSpaceBox": "EXCLUDE",
            		"MoovPlacement": "PROGRESSIVE_DOWNLOAD"        
            		}}}}
	    		if emf_VideoDescription is not 'none':
            			OutputGroupSettings['Settings'].update(emf_VideoDescription)
            		if emf_AudioDescription is not 'none':
				OutputGroupSettings['Settings'].update(emf_AudioDescription)
            		return OutputGroupSettings

        	elif s_container == '"mxf"':
            		OutputGroupSettings = {}
            		OutputGroupSettings ={
            		"Settings":{
            		"ContainerSettings": {
            		"Container": "MXF"
            		}}}
	    		if emf_VideoDescription is not 'none':
                		OutputGroupSettings['Settings'].update(emf_VideoDescription)
	    		if emf_AudioDescription is not 'none':
           			OutputGroupSettings['Settings'].update(emf_AudioDescription)
            
	    		return OutputGroupSettings
        else:
            print "Unknown Error Hit...exiting"
            exit()

        
        #if s_container == 'pcm':
        
        #else:
        #    print "Unknown Error Hit exiting"
        #    exit()

def translate_thumbnails(ets_preset_payload, etsid):
	

	
	emf_preset_thumbnail = {
  		"Description": etsid + ' Thumbnails',
  		"Name": etsid + ' Thumbnails',
  		"Settings": {
    		"VideoDescription": {
      		"ScalingBehavior": "DEFAULT",
      		"TimecodeInsertion": "DISABLED",
      		"AntiAlias": "ENABLED",
      		"Sharpness": 50,
      		"CodecSettings": {
        		"Codec": "FRAME_CAPTURE",
        		"FrameCaptureSettings": {
          		"FramerateNumerator": 1,
          		"FramerateDenominator": int(ets_preset_payload['Preset']['Thumbnails']['Interval']),
          		"MaxCaptures": 10000000,
          		"Quality": 80
        		}
      		},
      		"AfdSignaling": "NONE",
      		"DropFrameTimecode": "ENABLED",
      		"RespondToAfd": "NONE",
      		"ColorMetadata": "INSERT"
    		},
    		"ContainerSettings": {"Container": "RAW"}}}

	##Handle Auto Resolution
	if ets_preset_payload['Preset']['Video']['MaxWidth'] !=  'auto':
		emf_preset_thumbnail['Settings']['VideoDescription'].update({"Width" : int(ets_preset_payload['Preset']['Thumbnails']['MaxWidth'])})

	if ets_preset_payload['Preset']['Video']['MaxHeight'] !=  'auto':
		emf_preset_thumbnail['Settings']['VideoDescription'].update({"Height" : int(ets_preset_payload['Preset']['Thumbnails']['MaxHeight'])})	
	
	return emf_preset_thumbnail 

tregion = validation_region()
etsclient = boto.elastictranscoder.connect_to_region(tregion)
etsid, ets_preset_payload = validation_preset()
emf_outputgroup = validate_output(outputtype)

s_container = validate_container(ets_preset_payload, unsupport_container)
s_video = validate_video(ets_preset_payload, unsupport_video_codec)
s_audio = validate_audio(ets_preset_payload, unsupport_audio_codec)

if s_video is not 'none':
	emf_VideoDescription = translate_video(ets_preset_payload, s_video)
	emf_PresetThumbnails = translate_thumbnails(ets_preset_payload, etsid)
else:
	emf_VideoDescription = 'none'

if s_audio is not 'none':
	emf_AudioDesciption = translate_audio(ets_preset_payload,s_audio)
else:
	emf_AudioDesciption = 'none'

emf_PresetSettings = translate_container(emf_AudioDesciption,emf_VideoDescription,s_container,emf_outputgroup,s_video)

if ets_preset_payload['Preset']['Description'] == None:
	ts = time.time()	
	emf_Description = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H-%M-%S')
	emf_PresetSettings['Description'] = emf_Description
else:
	emf_PresetSettings['Description'] = ets_preset_payload['Preset']['Description']

if (len(ets_preset_payload['Preset']['Name']) > 40):
	ets_PresetName = ets_preset_payload['Preset']['Name']
	emf_PresetName = ets_PresetName[:40]
	emf_PresetSettings['Name'] = emf_PresetName
	print "WARNING: Warning name is greater than 40 characters, truncating... \n"
else:
	emf_PresetSettings['Name'] = ets_preset_payload['Preset']['Name']

if args.verbose == True:
	print '==================VERBOSE LOGGING=================='
    	print '====================PRESET====================='
    	print json.dumps(emf_PresetSettings,indent=4, sort_keys=False)
	print '====================THUMBNAILS====================='
	if args.save == True:
		print '==================SAVING FILES========================='
		file = open(etsid+".json", "w")
		file.write(json.dumps(emf_PresetSettings,indent=4, sort_keys=False))
		file.close()
	if s_video is not 'none':
    			print json.dumps(emf_PresetThumbnails,indent=4, sort_keys=False)
			if args.save == True:
				file = open(etsid + "_Thumbnail.json", "w")
                		file.write(json.dumps(emf_PresetThumbnails,indent=4, sort_keys=False))
                		file.close()
else: 
    	print json.dumps(emf_PresetSettings,indent=4, sort_keys=True)
	if args.save == True:
                print '==================SAVING FILES========================='
                file = open(etsid+".json", "w")
                file.write(json.dumps(emf_PresetSettings,indent=4, sort_keys=False))
                file.close()
    	print '====================THUMBNAILS====================='
        print '==================SAVING FILES========================='
    	if s_video is not 'none':
		print json.dumps(emf_PresetThumbnails,indent=4, sort_keys=False)
		if args.save == True:
                        file = open(etsid+"_Thumbnail.json", "w")
                        file.write(json.dumps(emf_PresetThumbnails,indent=4, sort_keys=False))
                        file.close()
##### To Do: ####
# detect audio only support for WAV/No container
# watermarks = image inserters
