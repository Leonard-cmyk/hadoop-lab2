import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.regex.*;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.*;
import org.apache.hadoop.mapreduce.*;
import org.apache.hadoop.mapreduce.lib.input.*;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

public class InvertedIndex {
    public static class IndexMapper extends Mapper<LongWritable, Text, Text, Text> {
        private final Set<String> stopwords = new HashSet<>();
        private static final Pattern WORD = Pattern.compile("[a-z]+");
        private String document;
        @Override protected void setup(Context context) throws IOException {
            document = ((FileSplit) context.getInputSplit()).getPath().getName();
            if (!document.matches("[A-Za-z0-9_.-]+"))
                throw new IOException("Use unique ASCII document filenames");
            for (String line : Files.readAllLines(new File("stopwords.txt").toPath(), StandardCharsets.UTF_8)) {
                String word = line.trim().toLowerCase(Locale.ROOT);
                if (!word.isEmpty()) stopwords.add(word);
            }
        }
        @Override protected void map(LongWritable key, Text value, Context context)
                throws IOException, InterruptedException {
            Matcher matcher = WORD.matcher(value.toString().toLowerCase(Locale.ROOT));
            while (matcher.find()) {
                String word = matcher.group();
                context.getCounter("Index", "RAW_TOKENS").increment(1);
                if (stopwords.contains(word)) {
                    context.getCounter("Index", "STOP_TOKENS").increment(1);
                } else {
                    context.write(new Text(word), new Text(document + "\t1"));
                    context.getCounter("Index", "KEPT_TOKENS").increment(1);
                }
            }
        }
    }
    static SortedMap<String, Long> counts(Iterable<Text> values) throws IOException {
        SortedMap<String, Long> counts = new TreeMap<>();
        for (Text value : values) {
            String[] fields = value.toString().split("\t", -1);
            if (fields.length != 2) throw new IOException("Invalid posting: " + value);
            long count = Long.parseLong(fields[1]);
            counts.put(fields[0], Math.addExact(counts.getOrDefault(fields[0], 0L), count));
        }
        return counts;
    }
    public static class CountCombiner extends Reducer<Text, Text, Text, Text> {
        @Override protected void reduce(Text word, Iterable<Text> values, Context context)
                throws IOException, InterruptedException {
            // Preserve the Mapper value format: the combiner may run zero or many times.
            for (Map.Entry<String, Long> entry : counts(values).entrySet())
                context.write(word, new Text(entry.getKey() + "\t" + entry.getValue()));
        }
    }
    public static class IndexReducer extends Reducer<Text, Text, Text, Text> {
        @Override protected void reduce(Text word, Iterable<Text> values, Context context)
                throws IOException, InterruptedException {
            StringBuilder result = new StringBuilder();
            long total = 0;
            for (Map.Entry<String, Long> entry : counts(values).entrySet()) {
                result.append('<').append(entry.getKey()).append(',').append(entry.getValue()).append(">;");
                total = Math.addExact(total, entry.getValue());
            }
            result.append("<total,").append(total).append(">.");
            context.write(word, new Text(result.toString()));
            context.getCounter("Index", "UNIQUE_WORDS").increment(1);
        }
    }
    public static void main(String[] args) throws Exception {
        if (args.length < 3 || args.length > 4) {
            System.err.println("Usage: InvertedIndex INPUT OUTPUT STOPWORDS_URI [no-combiner]");
            System.exit(2);
        }
        Configuration conf = new Configuration();
        Job job = Job.getInstance(conf, "Lab2 Inverted Index");
        job.setJarByClass(InvertedIndex.class);
        job.setMapperClass(IndexMapper.class);
        if (args.length == 3) job.setCombinerClass(CountCombiner.class);
        else if (!args[3].equals("no-combiner")) throw new IllegalArgumentException(args[3]);
        job.setReducerClass(IndexReducer.class);
        job.setMapOutputKeyClass(Text.class); job.setMapOutputValueClass(Text.class);
        job.setOutputKeyClass(Text.class); job.setOutputValueClass(Text.class);
        job.setNumReduceTasks(1);
        job.addCacheFile(java.net.URI.create(args[2] + "#stopwords.txt"));
        FileInputFormat.addInputPath(job, new Path(args[0]));
        if (System.getProperty("lab2.test.maxSplit") != null)
            FileInputFormat.setMaxInputSplitSize(job, Long.parseLong(System.getProperty("lab2.test.maxSplit")));
        FileOutputFormat.setOutputPath(job, new Path(args[1]));
        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
