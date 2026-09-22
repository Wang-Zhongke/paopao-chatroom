// Extract timestamped Chinese text from the lower portion of a captioned video.

#import <AVFoundation/AVFoundation.h>
#import <Foundation/Foundation.h>
#import <Vision/Vision.h>

static void Usage(void) {
    fprintf(stderr,
            "usage: burned_caption_ocr <video> <output.jsonl> [--start SEC] [--end SEC] "
            "[--step SEC] [--crop-top FRACTION] [--crop-bottom FRACTION]\n");
    exit(2);
}

static NSArray *Recognize(CGImageRef image, NSError **error) {
    VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
    request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
    request.recognitionLanguages = @[@"zh-Hans", @"en-US"];
    request.usesLanguageCorrection = YES;
    request.minimumTextHeight = 0.025;

    VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:image options:@{}];
    if (![handler performRequests:@[request] error:error]) {
        return @[];
    }

    NSMutableArray *items = [NSMutableArray array];
    for (VNRecognizedTextObservation *observation in request.results) {
        VNRecognizedText *candidate = [[observation topCandidates:1] firstObject];
        if (!candidate) continue;
        CGRect box = observation.boundingBox;
        [items addObject:@{
            @"text": candidate.string,
            @"confidence": @(candidate.confidence),
            @"x": @(box.origin.x),
            @"y": @(box.origin.y),
            @"width": @(box.size.width),
            @"height": @(box.size.height),
        }];
    }
    return items;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc < 3) Usage();
        NSString *inputPath = [NSString stringWithUTF8String:argv[1]];
        NSString *outputPath = [NSString stringWithUTF8String:argv[2]];
        double start = 0.0, end = -1.0, step = 0.8, cropTop = 0.50, cropBottom = 0.96;
        for (int i = 3; i < argc; i += 2) {
            if (i + 1 >= argc) Usage();
            NSString *flag = [NSString stringWithUTF8String:argv[i]];
            double value = strtod(argv[i + 1], NULL);
            if ([flag isEqualToString:@"--start"]) start = value;
            else if ([flag isEqualToString:@"--end"]) end = value;
            else if ([flag isEqualToString:@"--step"]) step = value;
            else if ([flag isEqualToString:@"--crop-top"]) cropTop = value;
            else if ([flag isEqualToString:@"--crop-bottom"]) cropBottom = value;
            else Usage();
        }
        if (start < 0 || step <= 0 || cropTop < 0 || cropBottom > 1 || cropTop >= cropBottom) Usage();

        AVURLAsset *asset = [AVURLAsset URLAssetWithURL:[NSURL fileURLWithPath:inputPath] options:nil];
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
        double duration = CMTimeGetSeconds(asset.duration);
#pragma clang diagnostic pop
        if (!isfinite(duration) || duration <= 0) {
            fprintf(stderr, "unable to read video duration\n");
            return 1;
        }
        double finish = end < 0 ? duration : fmin(end, duration);
        if (start >= finish) {
            fprintf(stderr, "start must be before video end\n");
            return 1;
        }

        [[NSFileManager defaultManager] createFileAtPath:outputPath contents:nil attributes:nil];
        NSFileHandle *output = [NSFileHandle fileHandleForWritingAtPath:outputPath];
        if (!output) {
            fprintf(stderr, "unable to open output\n");
            return 1;
        }

        AVAssetImageGenerator *generator = [[AVAssetImageGenerator alloc] initWithAsset:asset];
        generator.appliesPreferredTrackTransform = YES;
        generator.requestedTimeToleranceBefore = CMTimeMakeWithSeconds(0.08, 600);
        generator.requestedTimeToleranceAfter = CMTimeMakeWithSeconds(0.08, 600);

        int frame = 0;
        for (double timestamp = start; timestamp < finish; timestamp += step) {
            @autoreleasepool {
                CMTime requested = CMTimeMakeWithSeconds(timestamp, 600);
                CMTime actual = kCMTimeZero;
                NSError *frameError = nil;
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
                CGImageRef image = [generator copyCGImageAtTime:requested actualTime:&actual error:&frameError];
#pragma clang diagnostic pop
                if (!image) {
                    fprintf(stderr, "frame %d at %.2fs failed: %s\n", frame, timestamp,
                            frameError.localizedDescription.UTF8String);
                    frame++;
                    continue;
                }
                size_t width = CGImageGetWidth(image), height = CGImageGetHeight(image);
                CGRect cropRect = CGRectMake(0, floor(cropTop * height), width,
                                             fmin(ceil((cropBottom - cropTop) * height),
                                                  height - floor(cropTop * height)));
                CGImageRef cropped = CGImageCreateWithImageInRect(image, cropRect);
                NSError *ocrError = nil;
                NSArray *items = cropped ? Recognize(cropped, &ocrError) : @[];
                NSDictionary *row = @{
                    @"requested_seconds": @(timestamp),
                    @"actual_seconds": @(CMTimeGetSeconds(actual)),
                    @"frame_width": @(width),
                    @"frame_height": @(height),
                    @"crop_top": @(cropTop),
                    @"crop_bottom": @(cropBottom),
                    @"observations": items,
                    @"error": ocrError ? ocrError.localizedDescription : [NSNull null],
                };
                NSError *jsonError = nil;
                NSData *data = [NSJSONSerialization dataWithJSONObject:row options:0 error:&jsonError];
                if (data) {
                    [output writeData:data];
                    [output writeData:[NSData dataWithBytes:"\n" length:1]];
                }
                if (cropped) CGImageRelease(cropped);
                CGImageRelease(image);
            }
            frame++;
            if (frame % 100 == 0) {
                fprintf(stderr, "processed %d frames\n", frame);
            }
        }
        [output closeFile];
        NSDictionary *summary = @{
            @"input": inputPath,
            @"output": outputPath,
            @"duration_seconds": @(duration),
            @"start_seconds": @(start),
            @"end_seconds": @(finish),
            @"step_seconds": @(step),
            @"frames": @(frame),
        };
        NSData *summaryData = [NSJSONSerialization dataWithJSONObject:summary
                                                               options:NSJSONWritingPrettyPrinted | NSJSONWritingSortedKeys
                                                                 error:nil];
        printf("%s\n", [[[NSString alloc] initWithData:summaryData encoding:NSUTF8StringEncoding] UTF8String]);
    }
    return 0;
}
