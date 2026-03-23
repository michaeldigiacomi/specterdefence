using SQLite;
using SpecterAgent.Models;

namespace SpecterAgent.Data;

public class DatabaseContext
{
    private readonly SQLiteAsyncConnection _database;

    public DatabaseContext(string dbPath)
    {
        _database = new SQLiteAsyncConnection(dbPath);
        _database.CreateTableAsync<BufferedEvent>().Wait();
    }

    public async Task SaveEventAsync(EndpointEvent evt)
    {
        var json = Newtonsoft.Json.JsonConvert.SerializeObject(evt);
        await _database.InsertAsync(new BufferedEvent { EventJson = json, DetectedAt = evt.DetectedAt });
    }

    public async Task<List<BufferedEvent>> GetPendingEventsAsync(int limit)
    {
        return await _database.Table<BufferedEvent>()
                             .OrderBy(x => x.DetectedAt)
                             .Take(limit)
                             .ToListAsync();
    }

    public async Task DeleteEventsAsync(IEnumerable<int> ids)
    {
        foreach (var id in ids)
        {
            await _database.DeleteAsync<BufferedEvent>(id);
        }
    }
}

public class BufferedEvent
{
    [PrimaryKey, AutoIncrement]
    public int Id { get; set; }
    public string EventJson { get; set; } = string.Empty;
    public DateTime DetectedAt { get; set; }
}
