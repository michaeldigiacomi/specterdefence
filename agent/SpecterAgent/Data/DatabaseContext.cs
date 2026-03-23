using Microsoft.Data.Sqlite;
using SpecterAgent.Models;

namespace SpecterAgent.Data;

public class DatabaseContext
{
    private readonly string _connectionString;

    public DatabaseContext(string dbPath)
    {
        _connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = dbPath
        }.ToString();

        InitializeDatabase();
    }

    private void InitializeDatabase()
    {
        using var connection = new SqliteConnection(_connectionString);
        connection.Open();
        
        var command = connection.CreateCommand();
        command.CommandText = @"
            CREATE TABLE IF NOT EXISTS BufferedEvents (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                EventJson TEXT NOT NULL,
                DetectedAt TEXT NOT NULL
            )";
        command.ExecuteNonQuery();
    }

    public async Task SaveEventAsync(EndpointEvent evt)
    {
        var json = Newtonsoft.Json.JsonConvert.SerializeObject(evt);
        
        using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync();
        
        var command = connection.CreateCommand();
        command.CommandText = "INSERT INTO BufferedEvents (EventJson, DetectedAt) VALUES ($json, $date)";
        command.Parameters.AddWithValue("$json", json);
        command.Parameters.AddWithValue("$date", evt.DetectedAt.ToString("o"));
        
        await command.ExecuteNonQueryAsync();
    }

    public async Task<List<BufferedEvent>> GetPendingEventsAsync(int limit)
    {
        var events = new List<BufferedEvent>();
        
        using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync();
        
        var command = connection.CreateCommand();
        command.CommandText = "SELECT Id, EventJson, DetectedAt FROM BufferedEvents ORDER BY DetectedAt ASC LIMIT $limit";
        command.Parameters.AddWithValue("$limit", limit);
        
        using var reader = await command.ExecuteReaderAsync();
        while (await reader.ReadAsync())
        {
            events.Add(new BufferedEvent
            {
                Id = reader.GetInt32(0),
                EventJson = reader.GetString(1),
                DetectedAt = DateTime.Parse(reader.GetString(2))
            });
        }
        
        return events;
    }

    public async Task DeleteEventsAsync(IEnumerable<int> ids)
    {
        using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync();
        
        using var transaction = connection.BeginTransaction();
        
        foreach (var id in ids)
        {
            var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText = "DELETE FROM BufferedEvents WHERE Id = $id";
            command.Parameters.AddWithValue("$id", id);
            await command.ExecuteNonQueryAsync();
        }
        
        await transaction.CommitAsync();
    }
}

public class BufferedEvent
{
    public int Id { get; set; }
    public string EventJson { get; set; } = string.Empty;
    public DateTime DetectedAt { get; set; }
}
